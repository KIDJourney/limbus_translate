from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from .formatting import text_hash
from .json_paths import contains_hangul, get_path, is_translatable_path, iter_text_nodes
from .scanner import load_json


@dataclass(frozen=True)
class MemoryEntry:
    source_hash: str
    source_text: str
    target_text: str
    relative_file: str
    json_path: str


def build_memory(source_root: Path, target_root: Path) -> list[MemoryEntry]:
    entries: list[MemoryEntry] = []
    seen: set[tuple[str, str]] = set()
    for source_file in sorted(source_root.rglob("*.json")):
        relative = source_file.relative_to(source_root).as_posix()
        target_file = target_root / relative
        if not target_file.exists():
            continue
        source_data = load_json(source_file)
        target_data = load_json(target_file)
        for text_node in iter_text_nodes(source_data):
            if not is_translatable_path(text_node.path):
                continue
            if not contains_hangul(text_node.value):
                continue
            try:
                target_text = get_path(target_data, text_node.path)
            except (KeyError, IndexError, ValueError):
                continue
            if not isinstance(target_text, str) or not target_text.strip():
                continue
            if target_text == text_node.value or contains_hangul(target_text):
                continue
            key = (text_hash(text_node.value), target_text)
            if key in seen:
                continue
            seen.add(key)
            entries.append(
                MemoryEntry(
                    source_hash=text_hash(text_node.value),
                    source_text=text_node.value,
                    target_text=target_text,
                    relative_file=relative,
                    json_path=text_node.path_id,
                )
            )
    return entries


def write_memory(path: Path, entries: list[MemoryEntry]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump([asdict(entry) for entry in entries], handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def read_memory(path: Path) -> dict[str, MemoryEntry]:
    if not path.exists():
        return {}
    rows = json.loads(path.read_text(encoding="utf-8"))
    entries = [MemoryEntry(**row) for row in rows]
    return {entry.source_hash: entry for entry in entries}
