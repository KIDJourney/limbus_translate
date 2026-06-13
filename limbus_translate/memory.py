from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

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


@dataclass(frozen=True)
class MemoryRetrievalMatch:
    source_text: str
    target_text: str
    relative_file: str
    json_path: str
    source_similarity: float
    target_similarity: float


@dataclass(frozen=True)
class MemoryRetrievalCase:
    case_id: str
    source_text: str
    expected_text: str
    matches: list[MemoryRetrievalMatch]


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


def evaluate_memory_retrieval(
    *,
    cases: list[Any],
    memory: dict[str, MemoryEntry],
    top_k: int = 3,
    min_similarity: float = 0.35,
    thresholds: list[float] | None = None,
    include_exact: bool = False,
) -> dict[str, Any]:
    rows = [
        MemoryRetrievalCase(
            case_id=str(case.case_id),
            source_text=str(case.source_text),
            expected_text=str(case.expected_text),
            matches=find_similar_memory(
                source_text=str(case.source_text),
                expected_text=str(case.expected_text),
                memory=memory,
                top_k=top_k,
                min_similarity=min_similarity,
                include_exact=include_exact,
            ),
        )
        for case in cases
    ]
    return {
        "summary": summarize_memory_retrieval(rows, thresholds=thresholds or [min_similarity, 0.5, 0.7]),
        "cases": [asdict(row) for row in rows],
    }


def find_similar_memory(
    *,
    source_text: str,
    expected_text: str,
    memory: dict[str, MemoryEntry],
    top_k: int,
    min_similarity: float,
    include_exact: bool,
) -> list[MemoryRetrievalMatch]:
    source_hash = text_hash(source_text)
    matches: list[MemoryRetrievalMatch] = []
    for entry in memory.values():
        if not include_exact and entry.source_hash == source_hash:
            continue
        source_score = source_similarity(source_text, entry.source_text)
        if source_score < min_similarity:
            continue
        matches.append(
            MemoryRetrievalMatch(
                source_text=entry.source_text,
                target_text=entry.target_text,
                relative_file=entry.relative_file,
                json_path=entry.json_path,
                source_similarity=round(source_score, 4),
                target_similarity=round(text_similarity(expected_text, entry.target_text), 4),
            )
        )
    matches.sort(key=lambda item: (-item.source_similarity, -item.target_similarity, item.relative_file, item.json_path))
    return matches[:top_k]


def summarize_memory_retrieval(
    rows: list[MemoryRetrievalCase],
    *,
    thresholds: list[float],
) -> dict[str, Any]:
    total = len(rows)
    top_matches = [row.matches[0] for row in rows if row.matches]
    sweep = []
    for threshold in sorted(set(thresholds)):
        hits = [match for match in top_matches if match.source_similarity >= threshold]
        sweep.append(
            {
                "threshold": threshold,
                "matches": len(hits),
                "coverage": round(len(hits) / total, 4) if total else 0.0,
                "avg_target_similarity": round(sum(match.target_similarity for match in hits) / len(hits), 4)
                if hits
                else 0.0,
            }
        )
    return {
        "total": total,
        "with_match": len(top_matches),
        "coverage": round(len(top_matches) / total, 4) if total else 0.0,
        "avg_top_source_similarity": round(sum(match.source_similarity for match in top_matches) / len(top_matches), 4)
        if top_matches
        else 0.0,
        "avg_top_target_similarity": round(sum(match.target_similarity for match in top_matches) / len(top_matches), 4)
        if top_matches
        else 0.0,
        "thresholds": sweep,
    }


def write_memory_evaluation_report(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def source_similarity(left: str, right: str) -> float:
    return SequenceMatcher(None, normalize_similarity_text(left), normalize_similarity_text(right)).ratio()


def text_similarity(left: str, right: str) -> float:
    return SequenceMatcher(None, normalize_similarity_text(left), normalize_similarity_text(right)).ratio()


def normalize_similarity_text(value: str) -> str:
    return "".join(value.split()).lower()
