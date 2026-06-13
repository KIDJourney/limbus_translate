from __future__ import annotations

import hashlib
import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class TranslationCacheEntry:
    cache_key: str
    provider: str
    source_hash: str
    context_hash: str
    glossary_hash: str
    unit_id: str
    stable_key: str
    relative_file: str
    json_path: str
    source_text: str
    target_text: str
    created_at: str


@dataclass(frozen=True)
class TranslationTraceEntry:
    unit_id: str
    stable_key: str
    relative_file: str
    json_path: str
    source_hash: str
    source_text: str
    target_text: str
    translation_source: str
    provider: str
    cache_key: str
    context_hash: str
    glossary_hash: str
    glossary_terms: int


@dataclass(frozen=True)
class TranslationRequestLogEntry:
    cache_key: str
    provider: str
    source_hash: str
    context_hash: str
    glossary_hash: str
    unit_id: str
    stable_key: str
    relative_file: str
    json_path: str
    source_text: str
    glossary: list[tuple[str, str, str]]
    context: str
    created_at: str
    target_text: str = ""
    response_model: str = ""
    response_id: str = ""
    usage: dict[str, Any] = field(default_factory=dict)


def _utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def digest_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def glossary_digest(glossary: list[tuple[str, str, str]]) -> str:
    payload = json.dumps(glossary, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return digest_text(payload)


def build_cache_key(*, provider: str, source_hash: str, context: str, glossary: list[tuple[str, str, str]]) -> tuple[str, str, str]:
    context_hash = digest_text(context)
    glossary_hash = glossary_digest(glossary)
    payload = json.dumps(
        {
            "provider": provider,
            "source_hash": source_hash,
            "context_hash": context_hash,
            "glossary_hash": glossary_hash,
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return digest_text(payload), context_hash, glossary_hash


def make_cache_entry(
    *,
    cache_key: str,
    provider: str,
    source_hash: str,
    context_hash: str,
    glossary_hash: str,
    unit_id: str,
    stable_key: str,
    relative_file: str,
    json_path: str,
    source_text: str,
    target_text: str,
) -> TranslationCacheEntry:
    return TranslationCacheEntry(
        cache_key=cache_key,
        provider=provider,
        source_hash=source_hash,
        context_hash=context_hash,
        glossary_hash=glossary_hash,
        unit_id=unit_id,
        stable_key=stable_key,
        relative_file=relative_file,
        json_path=json_path,
        source_text=source_text,
        target_text=target_text,
        created_at=_utc_now(),
    )


def make_request_log_entry(
    *,
    cache_key: str,
    provider: str,
    source_hash: str,
    context_hash: str,
    glossary_hash: str,
    unit_id: str,
    stable_key: str,
    relative_file: str,
    json_path: str,
    source_text: str,
    glossary: list[tuple[str, str, str]],
    context: str,
    target_text: str = "",
    response_model: str = "",
    response_id: str = "",
    usage: dict[str, Any] | None = None,
) -> TranslationRequestLogEntry:
    return TranslationRequestLogEntry(
        cache_key=cache_key,
        provider=provider,
        source_hash=source_hash,
        context_hash=context_hash,
        glossary_hash=glossary_hash,
        unit_id=unit_id,
        stable_key=stable_key,
        relative_file=relative_file,
        json_path=json_path,
        source_text=source_text,
        glossary=glossary,
        context=context,
        created_at=_utc_now(),
        target_text=target_text,
        response_model=response_model,
        response_id=response_id,
        usage=usage or {},
    )


def read_translation_cache(path: Path) -> dict[str, TranslationCacheEntry]:
    if not path.exists():
        return {}
    rows = json.loads(path.read_text(encoding="utf-8"))
    return {row["cache_key"]: TranslationCacheEntry(**row) for row in rows if isinstance(row, dict) and row.get("cache_key")}


def write_translation_cache(path: Path, entries: dict[str, TranslationCacheEntry]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = sorted(entries.values(), key=lambda entry: (entry.relative_file, entry.json_path, entry.cache_key))
    path.write_text(json.dumps([asdict(entry) for entry in rows], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_translation_trace(path: Path, entries: list[TranslationTraceEntry]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for entry in entries:
            handle.write(json.dumps(asdict(entry), ensure_ascii=False, sort_keys=True))
            handle.write("\n")


def write_translation_request_log(path: Path, entries: list[TranslationRequestLogEntry]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for entry in entries:
            handle.write(json.dumps(asdict(entry), ensure_ascii=False, sort_keys=True))
            handle.write("\n")
