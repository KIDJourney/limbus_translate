from __future__ import annotations

import io
import subprocess
import tarfile
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class PreparedUpdate:
    repo: str
    base: str
    head: str
    changed_files: str
    source_baseline: str
    changed_count: int


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
