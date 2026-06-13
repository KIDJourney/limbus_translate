from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .formatting import looks_internal_identifier, profile_text, text_hash
from .json_paths import contains_hangul, get_path, is_translatable_path, iter_text_nodes


@dataclass(frozen=True)
class TranslationUnit:
    unit_id: str
    relative_file: str
    json_path: str
    source_text: str
    target_text: str | None
    reason: str
    source_hash: str
    target_hash: str | None
    placeholders: list[str]
    tags: list[str]
    numbers: list[str]
    line_breaks: int
    risk: str


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def dump_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def build_unit_id(relative_file: str, json_path: str, source_text: str) -> str:
    raw = f"{relative_file}\0{json_path}\0{source_text}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:16]


def classify_risk(relative_file: str, json_path: str, source_text: str) -> str:
    if relative_file.startswith("StoryData/") or ".content" in json_path or ".dlg" in json_path:
        return "high"
    if ".desc" in json_path or ".message" in json_path or ".story" in json_path:
        return "medium"
    if looks_internal_identifier(source_text):
        return "internal"
    return "low"


def is_script_direction(text: str) -> bool:
    stripped = text.strip()
    if stripped.startswith("//"):
        return True
    if stripped in {"(더미)", "더미"}:
        return True
    if "에피소드" in stripped and ("S" in stripped or "_" in stripped):
        return True
    return False


def should_suppress_same_source(relative_file: str, json_path: str, source_text: str) -> bool:
    key = json_path.split(".")[-1]
    if key in {"name", "title", "subDesc", "prevDesc", "teller", "summary"} and looks_internal_identifier(source_text):
        return True
    if key == "subDesc" and any(marker in source_text for marker in ["사용 안하는", "subDesc"]):
        return True
    if key == "summary" and source_text in {"표시용"}:
        return True
    if key == "name" and any(marker in source_text for marker in ["선택지", "이벤트", "버프 이름", "사용하지않는", "번역x"]):
        return True
    if key == "name" and any(marker in source_text for marker in ["이펙트", "효과"]):
        return True
    if key == "desc" and source_text in {"사용 안하는 텍스트", "적 잡몹", "더미"}:
        return True
    if key == "desc" and any(marker in source_text for marker in ["표시용", "번역해주세요"]):
        return True
    if key == "desc" and looks_internal_identifier(source_text):
        return True
    if key == "desc" and relative_file.startswith("BattleSpeechBubbleDlg"):
        return True
    if key == "content" and is_script_direction(source_text):
        return True
    return False


def scan_missing(source_root: Path, target_root: Path, *, include_internal: bool = False) -> list[TranslationUnit]:
    units: list[TranslationUnit] = []
    for source_file in sorted(source_root.rglob("*.json")):
        relative = source_file.relative_to(source_root).as_posix()
        target_file = target_root / relative
        source_data = load_json(source_file)
        target_data = load_json(target_file) if target_file.exists() else None
        for text_node in iter_text_nodes(source_data):
            if not is_translatable_path(text_node.path):
                continue
            if not contains_hangul(text_node.value):
                continue
            target_text: str | None = None
            reason = "missing_target_file"
            if target_data is not None:
                try:
                    candidate = get_path(target_data, text_node.path)
                    if isinstance(candidate, str):
                        target_text = candidate
                        if candidate.strip() and candidate != text_node.value:
                            continue
                        if candidate == text_node.value and not include_internal:
                            if should_suppress_same_source(relative, text_node.path_id, text_node.value):
                                continue
                        reason = "target_same_as_source" if candidate.strip() else "missing_target_text"
                    else:
                        reason = "target_path_not_text"
                except (KeyError, IndexError, ValueError):
                    reason = "missing_target_path"
            source_profile = profile_text(text_node.value)
            units.append(
                TranslationUnit(
                    unit_id=build_unit_id(relative, text_node.path_id, text_node.value),
                    relative_file=relative,
                    json_path=text_node.path_id,
                    source_text=text_node.value,
                    target_text=target_text,
                    reason=reason,
                    source_hash=source_profile.source_hash,
                    target_hash=text_hash(target_text) if target_text is not None else None,
                    placeholders=source_profile.placeholders,
                    tags=source_profile.tags,
                    numbers=source_profile.numbers,
                    line_breaks=source_profile.line_breaks,
                    risk=classify_risk(relative, text_node.path_id, text_node.value),
                )
            )
    return units


def write_units(path: Path, units: list[TranslationUnit]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = [asdict(unit) for unit in units]
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
