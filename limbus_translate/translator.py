from __future__ import annotations

import copy
from pathlib import Path

from .glossary import GlossaryTerm, match_terms
from .json_paths import set_path
from .memory import MemoryEntry
from .providers import TranslationProvider, TranslationRequest
from .scanner import TranslationUnit, dump_json, load_json


def translate_units(
    *,
    source_root: Path,
    target_root: Path,
    output_root: Path,
    units: list[TranslationUnit],
    glossary: list[GlossaryTerm],
    provider: TranslationProvider,
    memory: dict[str, MemoryEntry] | None = None,
    limit: int | None = None,
) -> int:
    changed_files: dict[str, object] = {}
    selected = units[:limit] if limit is not None else units
    for unit in selected:
        source_file = source_root / unit.relative_file
        target_file = target_root / unit.relative_file
        if unit.relative_file not in changed_files:
            changed_files[unit.relative_file] = load_json(target_file if target_file.exists() else source_file)
        memory_entry = (memory or {}).get(unit.source_hash)
        if memory_entry is not None:
            translated = memory_entry.target_text
        else:
            matched = match_terms(unit.source_text, glossary)
            translated = provider.translate(
                TranslationRequest(
                    source_text=unit.source_text,
                    glossary=[(term.source, term.target, term.note) for term in matched],
                    context=f"{unit.relative_file}::{unit.json_path}; risk={unit.risk}",
                )
            )
        path = tuple(unit.json_path.split("."))
        set_path(changed_files[unit.relative_file], path, translated)
    for relative_file, data in changed_files.items():
        dump_json(output_root / relative_file, data)
    return len(selected)


def overlay_existing_target(source_root: Path, target_root: Path, output_root: Path) -> None:
    for source_file in source_root.rglob("*.json"):
        relative = source_file.relative_to(source_root)
        target_file = target_root / relative
        data = copy.deepcopy(load_json(target_file if target_file.exists() else source_file))
        dump_json(output_root / relative, data)
