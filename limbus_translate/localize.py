from __future__ import annotations

import io
import json
import subprocess
import tarfile
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path

from .scanner import TranslationUnit
from .state import LOCKED_STATUSES, UnitState, state_for_unit


@dataclass(frozen=True)
class PreparedUpdate:
    repo: str
    base: str
    head: str
    changed_files: str
    source_baseline: str
    changed_count: int


@dataclass(frozen=True)
class PatchResult:
    patch: str
    target_dir: str
    replacements: int
    changed_files: list[str]
    apply_check: bool
    skipped_units: int


def prepare_localize_update(
    *,
    repo: Path,
    base: str,
    head: str,
    work_dir: Path,
    language_dir: str = "KR",
) -> PreparedUpdate:
    work_dir.mkdir(parents=True, exist_ok=True)
    changed_files_path = work_dir / "changed-files.txt"
    source_baseline_root = work_dir / "source-baseline"
    source_baseline_root.mkdir(parents=True, exist_ok=True)

    changed_files = git_lines(repo, ["diff", "--name-only", base, head])
    changed_files_path.write_text("\n".join(changed_files) + ("\n" if changed_files else ""), encoding="utf-8")

    archive = git_bytes(repo, ["archive", base, language_dir])
    extract_tar_safely(archive, source_baseline_root)

    return PreparedUpdate(
        repo=str(repo),
        base=base,
        head=head,
        changed_files=str(changed_files_path),
        source_baseline=str(source_baseline_root / language_dir),
        changed_count=len(changed_files),
    )


def git_lines(repo: Path, args: list[str]) -> list[str]:
    output = git_bytes(repo, args).decode("utf-8")
    return [line for line in output.splitlines() if line.strip()]


def git_bytes(repo: Path, args: list[str]) -> bytes:
    completed = subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return completed.stdout


def extract_tar_safely(archive: bytes, destination: Path) -> None:
    destination = destination.resolve()
    with tarfile.open(fileobj=io.BytesIO(archive), mode="r:*") as tar:
        for member in tar.getmembers():
            target = (destination / member.name).resolve()
            if destination != target and destination not in target.parents:
                raise ValueError(f"unsafe archive path: {member.name}")
        tar.extractall(destination)


def prepared_update_payload(update: PreparedUpdate) -> dict[str, str | int]:
    return asdict(update)


def make_translation_patch(
    *,
    repo: Path,
    units: list[TranslationUnit],
    states: dict[str, UnitState],
    patch_path: Path,
    target_dir: str = "LLC_zh-CN",
) -> PatchResult:
    patch_path.parent.mkdir(parents=True, exist_ok=True)
    patch_path = patch_path.resolve()
    repo = repo.resolve()
    with tempfile.TemporaryDirectory(prefix="limbus-translate-patch-") as tmp:
        worktree = Path(tmp) / "worktree"
        run_git(repo, ["worktree", "add", "--detach", str(worktree), "HEAD"])
        try:
            replacements, skipped_units = apply_reviewed_replacements(
                target_root=worktree / target_dir,
                units=units,
                states=states,
            )
            diff = git_bytes(worktree, ["diff", "--", target_dir])
        finally:
            run_git(repo, ["worktree", "remove", "--force", str(worktree)])
        patch_path.write_bytes(diff)
    apply_check = False
    if patch_path.stat().st_size:
        run_git(repo, ["apply", "--check", str(patch_path)])
        apply_check = True
    changed_files = patch_changed_files(patch_path)
    return PatchResult(
        patch=str(patch_path),
        target_dir=target_dir,
        replacements=replacements,
        changed_files=changed_files,
        apply_check=apply_check,
        skipped_units=skipped_units,
    )


def apply_reviewed_replacements(
    *,
    target_root: Path,
    units: list[TranslationUnit],
    states: dict[str, UnitState],
) -> tuple[int, int]:
    by_file: dict[str, list[tuple[TranslationUnit, UnitState]]] = {}
    skipped_units = 0
    for unit in units:
        state = state_for_unit(unit, states)
        if state is None or state.status not in LOCKED_STATUSES or not state.target_text:
            skipped_units += 1
            continue
        by_file.setdefault(unit.relative_file, []).append((unit, state))

    replacements = 0
    for relative_file, items in sorted(by_file.items()):
        path = target_root / relative_file
        if not path.exists():
            raise FileNotFoundError(f"target file does not exist for patch generation: {path}")
        text = path.read_text(encoding="utf-8-sig")
        for unit, state in sorted(items, key=lambda item: path_sort_key(item[0].json_path), reverse=True):
            updated, changed = replace_json_string_at_path(text, tuple(unit.json_path.split(".")), state.target_text or "")
            text = updated
            if changed:
                replacements += 1
        path.write_text(text, encoding="utf-8")
    return replacements, skipped_units


def replace_json_string_at_path(text: str, path: tuple[str, ...], target_text: str) -> tuple[str, bool]:
    start, end, current = find_json_string_span(text, path)
    if current == target_text:
        return text, False
    replacement = json.dumps(target_text, ensure_ascii=False)
    return f"{text[:start]}{replacement}{text[end:]}", True


def find_json_string_span(text: str, path: tuple[str, ...]) -> tuple[int, int, str]:
    return find_value_span(text, skip_ws(text, 0), path)


def find_value_span(text: str, pos: int, path: tuple[str, ...]) -> tuple[int, int, str]:
    pos = skip_ws(text, pos)
    if not path:
        if pos >= len(text) or text[pos] != '"':
            raise ValueError("target JSON path is not a string value")
        return parse_string(text, pos)
    if pos >= len(text):
        raise ValueError("unexpected end of JSON while resolving path")
    if text[pos] == "{":
        return find_object_value_span(text, pos, path)
    if text[pos] == "[":
        return find_array_value_span(text, pos, path)
    raise ValueError(f"cannot descend into JSON scalar at path component {path[0]!r}")


def find_object_value_span(text: str, pos: int, path: tuple[str, ...]) -> tuple[int, int, str]:
    wanted = path[0]
    pos = skip_ws(text, pos + 1)
    if pos < len(text) and text[pos] == "}":
        raise KeyError(wanted)
    while pos < len(text):
        key_start = skip_ws(text, pos)
        _start, key_end, key = parse_string(text, key_start)
        colon = skip_ws(text, key_end)
        if colon >= len(text) or text[colon] != ":":
            raise ValueError("expected ':' after JSON object key")
        value_start = skip_ws(text, colon + 1)
        if key == wanted:
            return find_value_span(text, value_start, path[1:])
        pos = skip_json_value(text, value_start)
        pos = skip_ws(text, pos)
        if pos < len(text) and text[pos] == ",":
            pos += 1
            continue
        if pos < len(text) and text[pos] == "}":
            break
        raise ValueError("expected ',' or '}' in JSON object")
    raise KeyError(wanted)


def find_array_value_span(text: str, pos: int, path: tuple[str, ...]) -> tuple[int, int, str]:
    wanted = path[0]
    if not wanted.isdigit():
        raise KeyError(wanted)
    wanted_index = int(wanted)
    index = 0
    pos = skip_ws(text, pos + 1)
    if pos < len(text) and text[pos] == "]":
        raise IndexError(wanted_index)
    while pos < len(text):
        value_start = skip_ws(text, pos)
        if index == wanted_index:
            return find_value_span(text, value_start, path[1:])
        pos = skip_json_value(text, value_start)
        pos = skip_ws(text, pos)
        if pos < len(text) and text[pos] == ",":
            pos += 1
            index += 1
            continue
        if pos < len(text) and text[pos] == "]":
            break
        raise ValueError("expected ',' or ']' in JSON array")
    raise IndexError(wanted_index)


def parse_string(text: str, pos: int) -> tuple[int, int, str]:
    if pos >= len(text) or text[pos] != '"':
        raise ValueError("expected JSON string")
    idx = pos + 1
    escaped = False
    while idx < len(text):
        char = text[idx]
        if escaped:
            escaped = False
        elif char == "\\":
            escaped = True
        elif char == '"':
            end = idx + 1
            return pos, end, json.loads(text[pos:end])
        idx += 1
    raise ValueError("unterminated JSON string")


def skip_json_value(text: str, pos: int) -> int:
    _value, end = json.JSONDecoder().raw_decode(text, skip_ws(text, pos))
    return end


def skip_ws(text: str, pos: int) -> int:
    while pos < len(text) and text[pos] in " \t\r\n":
        pos += 1
    return pos


def path_sort_key(path: str) -> tuple[int, ...]:
    result = []
    for part in path.split("."):
        result.append(int(part) if part.isdigit() else -1)
    return tuple(result)


def patch_changed_files(patch_path: Path) -> list[str]:
    files: list[str] = []
    if not patch_path.exists():
        return files
    for line in patch_path.read_text(encoding="utf-8").splitlines():
        if line.startswith("diff --git "):
            parts = line.split()
            if len(parts) >= 4:
                files.append(parts[2][2:] if parts[2].startswith("a/") else parts[2])
    return files


def run_git(repo: Path, args: list[str]) -> None:
    subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
