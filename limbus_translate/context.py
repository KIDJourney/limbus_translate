from __future__ import annotations

import json
from difflib import SequenceMatcher
from dataclasses import asdict, dataclass
from typing import Any

from .glossary import GlossaryTerm
from .json_paths import contains_hangul, get_path, is_translatable_path, iter_text_nodes
from .memory import MemoryEntry
from .scanner import TranslationUnit


@dataclass(frozen=True)
class ContextTerm:
    source: str
    target: str
    note: str


@dataclass(frozen=True)
class ContextSnippet:
    role: str
    relative_file: str
    json_path: str
    source_text: str
    target_text: str
    score: float = 0.0


@dataclass(frozen=True)
class TranslationContextBundle:
    relative_file: str
    json_path: str
    source_json_path: str
    stable_key: str | None
    risk: str
    terms: list[ContextTerm]
    neighbors: list[ContextSnippet]
    memory_examples: list[ContextSnippet]

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False, sort_keys=True)


def build_translation_context(
    *,
    unit: TranslationUnit,
    source_data: Any,
    target_data: Any,
    matched_terms: list[GlossaryTerm],
    memory: dict[str, MemoryEntry],
    neighbor_window: int = 2,
    max_memory_examples: int = 5,
) -> TranslationContextBundle:
    return TranslationContextBundle(
        relative_file=unit.relative_file,
        json_path=unit.json_path,
        source_json_path=unit.source_json_path or unit.json_path,
        stable_key=unit.stable_key,
        risk=unit.risk,
        terms=[ContextTerm(term.source, term.target, term.note) for term in matched_terms],
        neighbors=neighbor_snippets(unit, source_data, target_data, window=neighbor_window),
        memory_examples=memory_snippets(unit, memory, limit=max_memory_examples),
    )


def neighbor_snippets(
    unit: TranslationUnit,
    source_data: Any,
    target_data: Any,
    *,
    window: int,
) -> list[ContextSnippet]:
    nodes = [node for node in iter_text_nodes(source_data) if is_translatable_path(node.path)]
    source_path = unit.source_json_path or unit.json_path
    center = next((idx for idx, node in enumerate(nodes) if node.path_id == source_path), None)
    if center is None:
        return []

    start = max(0, center - window)
    end = min(len(nodes), center + window + 1)
    snippets: list[ContextSnippet] = []
    for idx in range(start, end):
        if idx == center:
            continue
        node = nodes[idx]
        target_text = ""
        try:
            candidate = get_path(target_data, node.path)
        except (KeyError, IndexError, ValueError, TypeError):
            candidate = ""
        if isinstance(candidate, str) and candidate != node.value and not contains_hangul(candidate):
            target_text = candidate
        role = "previous" if idx < center else "next"
        snippets.append(
            ContextSnippet(
                role=role,
                relative_file=unit.relative_file,
                json_path=node.path_id,
                source_text=node.value,
                target_text=target_text,
            )
        )
    return snippets


def memory_snippets(
    unit: TranslationUnit,
    memory: dict[str, MemoryEntry],
    *,
    limit: int,
    min_similarity: float = 0.35,
) -> list[ContextSnippet]:
    scored_entries: list[tuple[float, int, MemoryEntry]] = []
    for entry in memory.values():
        if entry.source_hash == unit.source_hash:
            continue
        score = source_similarity(unit.source_text, entry.source_text)
        same_file = 1 if entry.relative_file == unit.relative_file else 0
        if same_file or score >= min_similarity:
            scored_entries.append((score, same_file, entry))
    scored_entries.sort(key=lambda item: (-item[1], -item[0], item[2].relative_file, item[2].json_path))
    return [
        ContextSnippet(
            role="memory" if same_file else "similar_memory",
            relative_file=entry.relative_file,
            json_path=entry.json_path,
            source_text=entry.source_text,
            target_text=entry.target_text,
            score=round(score, 4),
        )
        for score, same_file, entry in scored_entries[:limit]
    ]


def source_similarity(left: str, right: str) -> float:
    left_norm = " ".join(left.split())
    right_norm = " ".join(right.split())
    if not left_norm or not right_norm:
        return 0.0
    return SequenceMatcher(None, left_norm, right_norm).ratio()
