from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

from .context import build_translation_context
from .glossary import GlossaryTerm, match_terms
from .json_paths import get_path, set_path
from .lore import LoreEntry, LoreIndex
from .memory import MemoryEntry
from .providers import TranslationProvider, TranslationRequest, provider_metadata
from .scanner import TranslationUnit, dump_json, get_data_list_match, load_json
from .state import UnitState, is_locked, state_for_unit
from .translation_cache import (
    TranslationCacheEntry,
    TranslationRequestLogEntry,
    TranslationTraceEntry,
    build_cache_key,
    make_cache_entry,
    make_request_log_entry,
)


def ensure_missing_data_list_record(output_data: Any, source_data: Any, unit: TranslationUnit) -> tuple[str, ...]:
    source_path = tuple((unit.source_json_path or unit.json_path).split("."))
    match = get_data_list_match(source_data, source_path)
    if match is None:
        return tuple(unit.json_path.split("."))
    prefix, record_index, suffix, record_id = match
    records = get_path(output_data, prefix)
    if not isinstance(records, list):
        return tuple(unit.json_path.split("."))
    for idx, record in enumerate(records):
        if isinstance(record, dict) and record.get("id") == record_id:
            return (*prefix, str(idx), *suffix)
    source_records = get_path(source_data, prefix)
    source_record = copy.deepcopy(source_records[record_index])
    records.append(source_record)
    return (*prefix, str(len(records) - 1), *suffix)


def translate_units(
    *,
    source_root: Path,
    target_root: Path,
    output_root: Path,
    units: list[TranslationUnit],
    glossary: list[GlossaryTerm],
    provider: TranslationProvider,
    memory: dict[str, MemoryEntry] | None = None,
    lore_entries: list[LoreEntry] | None = None,
    lore_index: LoreIndex | None = None,
    states: dict[str, UnitState] | None = None,
    candidate_cache: dict[str, TranslationCacheEntry] | None = None,
    candidate_cache_updates: list[TranslationCacheEntry] | None = None,
    request_log: list[TranslationRequestLogEntry] | None = None,
    trace: list[TranslationTraceEntry] | None = None,
    provider_name: str = "",
    limit: int | None = None,
) -> int:
    changed_files: dict[str, object] = {}
    source_cache: dict[str, object] = {}
    selected = units[:limit] if limit is not None else units
    processed_count = 0
    for unit in selected:
        translation_source = ""
        cache_key = ""
        context_hash = ""
        glossary_hash = ""
        glossary_terms = 0
        state = state_for_unit(unit, states or {})
        if state is not None and state.target_text:
            translated = state.target_text
            translation_source = f"state:{state.status}"
        elif is_locked(unit, states or {}):
            continue
        else:
            translated = ""
        source_file = source_root / unit.relative_file
        target_file = target_root / unit.relative_file
        if unit.relative_file not in changed_files:
            changed_files[unit.relative_file] = load_json(target_file if target_file.exists() else source_file)
        if unit.relative_file not in source_cache:
            source_cache[unit.relative_file] = load_json(source_file)
        if not translated:
            memory_entry = (memory or {}).get(unit.source_hash)
            if memory_entry is not None:
                translated = memory_entry.target_text
                translation_source = "memory"
            else:
                matched = match_terms(unit.source_text, glossary)
                request_glossary = [(term.source, term.target, term.note) for term in matched]
                glossary_terms = len(request_glossary)
                context = build_translation_context(
                    unit=unit,
                    source_data=source_cache[unit.relative_file],
                    target_data=changed_files[unit.relative_file],
                    matched_terms=matched,
                    memory=memory or {},
                    lore_entries=lore_entries or [],
                    lore_index=lore_index,
                )
                context_json = context.to_json()
                cache_key, context_hash, glossary_hash = build_cache_key(
                    provider=provider_name,
                    source_hash=unit.source_hash,
                    context=context_json,
                    glossary=request_glossary,
                )
                cached = (candidate_cache or {}).get(cache_key)
                if cached is not None:
                    translated = cached.target_text
                    translation_source = "candidate_cache"
                else:
                    translated = provider.translate(
                        TranslationRequest(
                            source_text=unit.source_text,
                            glossary=request_glossary,
                            context=context_json,
                        )
                    )
                    translation_source = "provider"
                    if request_log is not None:
                        metadata = provider_metadata(provider)
                        request_log.append(
                            make_request_log_entry(
                                cache_key=cache_key,
                                provider=provider_name,
                                source_hash=unit.source_hash,
                                context_hash=context_hash,
                                glossary_hash=glossary_hash,
                                unit_id=unit.unit_id,
                                stable_key=unit.stable_key,
                                relative_file=unit.relative_file,
                                json_path=unit.json_path,
                                source_text=unit.source_text,
                                glossary=request_glossary,
                                context=context_json,
                                target_text=translated,
                                response_model=str(metadata.get("response_model", "")),
                                response_id=str(metadata.get("response_id", "")),
                                usage=metadata.get("usage", {}) if isinstance(metadata.get("usage", {}), dict) else {},
                            )
                        )
                    if candidate_cache_updates is not None:
                        candidate_cache_updates.append(
                            make_cache_entry(
                                cache_key=cache_key,
                                provider=provider_name,
                                source_hash=unit.source_hash,
                                context_hash=context_hash,
                                glossary_hash=glossary_hash,
                                unit_id=unit.unit_id,
                                stable_key=unit.stable_key,
                                relative_file=unit.relative_file,
                                json_path=unit.json_path,
                                source_text=unit.source_text,
                                target_text=translated,
                            )
                        )
        if unit.reason == "missing_target_record":
            path = ensure_missing_data_list_record(
                changed_files[unit.relative_file],
                source_cache[unit.relative_file],
                unit,
            )
        else:
            path = tuple(unit.json_path.split("."))
        set_path(changed_files[unit.relative_file], path, translated)
        if trace is not None:
            trace.append(
                TranslationTraceEntry(
                    unit_id=unit.unit_id,
                    stable_key=unit.stable_key,
                    relative_file=unit.relative_file,
                    json_path=unit.json_path,
                    source_hash=unit.source_hash,
                    source_text=unit.source_text,
                    target_text=translated,
                    translation_source=translation_source,
                    provider=provider_name,
                    cache_key=cache_key,
                    context_hash=context_hash,
                    glossary_hash=glossary_hash,
                    glossary_terms=glossary_terms,
                )
            )
        processed_count += 1
    for relative_file, data in changed_files.items():
        dump_json(output_root / relative_file, data)
    return processed_count


def apply_state_translations(
    *,
    source_root: Path,
    target_root: Path,
    output_root: Path,
    units: list[TranslationUnit],
    states: dict[str, UnitState],
    limit: int | None = None,
) -> int:
    changed_files: dict[str, object] = {}
    source_cache: dict[str, object] = {}
    selected = units[:limit] if limit is not None else units
    applied_count = 0
    for unit in selected:
        state = state_for_unit(unit, states)
        if state is None or not state.target_text:
            continue
        source_file = source_root / unit.relative_file
        target_file = target_root / unit.relative_file
        if unit.relative_file not in changed_files:
            changed_files[unit.relative_file] = load_json(target_file if target_file.exists() else source_file)
        if unit.relative_file not in source_cache:
            source_cache[unit.relative_file] = load_json(source_file)
        if unit.reason == "missing_target_record":
            path = ensure_missing_data_list_record(
                changed_files[unit.relative_file],
                source_cache[unit.relative_file],
                unit,
            )
        else:
            path = tuple(unit.json_path.split("."))
        set_path(changed_files[unit.relative_file], path, state.target_text)
        applied_count += 1
    for relative_file, data in changed_files.items():
        dump_json(output_root / relative_file, data)
    return applied_count


def overlay_existing_target(source_root: Path, target_root: Path, output_root: Path) -> None:
    for source_file in source_root.rglob("*.json"):
        relative = source_file.relative_to(source_root)
        target_file = target_root / relative
        data = copy.deepcopy(load_json(target_file if target_file.exists() else source_file))
        dump_json(output_root / relative, data)
