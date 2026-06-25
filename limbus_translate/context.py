from __future__ import annotations

import json
import re
from collections import defaultdict
from difflib import SequenceMatcher
from dataclasses import asdict, dataclass
from typing import Any

from .glossary import GlossaryTerm
from .json_paths import contains_hangul, get_path, is_translatable_path, iter_text_nodes
from .lore import LoreEntry, LoreIndex, LoreMatch, match_lore, match_lore_index
from .memory import MemoryEntry
from .scanner import TranslationUnit

TOKEN_RE = re.compile(r"[가-힣A-Za-z0-9]+")
MAX_MEMORY_PREFILTER_CANDIDATES = 250
MEMORY_BIGRAM_WEIGHT = 0.25


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
class ContextLore:
    title: str
    text: str
    tags: list[str]
    source: str
    anchors: list[str]
    score: float = 0.0


@dataclass(frozen=True)
class MemoryIndex:
    by_file: dict[str, list[MemoryEntry]]
    by_token: dict[str, list[MemoryEntry]]
    by_bigram: dict[str, list[MemoryEntry]]


MEMORY_INDEX_CACHE: dict[int, tuple[int, MemoryIndex]] = {}


@dataclass(frozen=True)
class TranslationContextBundle:
    relative_file: str
    json_path: str
    source_json_path: str
    stable_key: str | None
    reason: str
    risk: str
    previous_target_text: str
    terms: list[ContextTerm]
    neighbors: list[ContextSnippet]
    memory_examples: list[ContextSnippet]
    lore: list[ContextLore]

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False, sort_keys=True)


def build_translation_context(
    *,
    unit: TranslationUnit,
    source_data: Any,
    target_data: Any,
    matched_terms: list[GlossaryTerm],
    memory: dict[str, MemoryEntry],
    lore_entries: list[LoreEntry] | None = None,
    lore_index: LoreIndex | None = None,
    neighbor_window: int = 2,
    max_memory_examples: int = 5,
    max_lore_entries: int = 5,
) -> TranslationContextBundle:
    if lore_index is not None:
        lore_matches = match_lore_index(unit.source_text, lore_index, terms=matched_terms, limit=max_lore_entries)
    else:
        lore_matches = match_lore(unit.source_text, lore_entries or [], terms=matched_terms, limit=max_lore_entries)
    return TranslationContextBundle(
        relative_file=unit.relative_file,
        json_path=unit.json_path,
        source_json_path=unit.source_json_path or unit.json_path,
        stable_key=unit.stable_key,
        reason=unit.reason,
        risk=unit.risk,
        previous_target_text=previous_target_text(unit),
        terms=[ContextTerm(term.source, term.target, term.note) for term in matched_terms],
        neighbors=neighbor_snippets(unit, source_data, target_data, window=neighbor_window),
        memory_examples=memory_snippets(unit, memory, limit=max_memory_examples),
        lore=lore_context(lore_matches),
    )


def previous_target_text(unit: TranslationUnit) -> str:
    if unit.reason != "source_changed":
        return ""
    if not unit.target_text:
        return ""
    if contains_hangul(unit.target_text):
        return ""
    return unit.target_text


def lore_context(matches: list[LoreMatch]) -> list[ContextLore]:
    return [
        ContextLore(
            title=match.title,
            text=match.text,
            tags=match.tags,
            source=match.source,
            anchors=match.anchors,
            score=match.score,
        )
        for match in matches
    ]


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
    max_prefilter_candidates: int = MAX_MEMORY_PREFILTER_CANDIDATES,
) -> list[ContextSnippet]:
    query_tokens = lexical_tokens(unit.source_text)
    query_bigrams = hangul_bigrams(unit.source_text)
    index = get_memory_index(memory)
    candidate_map: dict[str, tuple[float, int, MemoryEntry]] = {}

    def add_candidate(entry: MemoryEntry, score_delta: float, same_file: int) -> None:
        if entry.source_hash == unit.source_hash:
            return
        current = candidate_map.get(entry.source_hash)
        if current is None:
            candidate_map[entry.source_hash] = (score_delta, same_file, entry)
            return
        score, existing_same_file, existing_entry = current
        candidate_map[entry.source_hash] = (score + score_delta, max(existing_same_file, same_file), existing_entry)

    for entry in index.by_file.get(unit.relative_file, []):
        add_candidate(entry, 1.0, 1)
    for token in query_tokens:
        for entry in index.by_token.get(token, []):
            add_candidate(entry, 1.0, 0)
    for bigram in query_bigrams:
        for entry in index.by_bigram.get(bigram, []):
            add_candidate(entry, MEMORY_BIGRAM_WEIGHT, 0)

    candidates = [
        (score, same_file, entry)
        for score, same_file, entry in candidate_map.values()
        if same_file or score >= 0.5
    ]
    candidates.sort(key=lambda item: (-item[1], -item[0], item[2].relative_file, item[2].json_path))

    scored_entries: list[tuple[float, int, MemoryEntry]] = []
    for _, same_file, entry in candidates[:max_prefilter_candidates]:
        score = source_similarity(unit.source_text, entry.source_text)
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


def get_memory_index(memory: dict[str, MemoryEntry]) -> MemoryIndex:
    cache_key = id(memory)
    cached = MEMORY_INDEX_CACHE.get(cache_key)
    if cached is not None and cached[0] == len(memory):
        return cached[1]

    by_file: dict[str, list[MemoryEntry]] = defaultdict(list)
    by_token: dict[str, list[MemoryEntry]] = defaultdict(list)
    by_bigram: dict[str, list[MemoryEntry]] = defaultdict(list)
    for entry in memory.values():
        by_file[entry.relative_file].append(entry)
        for token in lexical_tokens(entry.source_text):
            by_token[token].append(entry)
        for bigram in hangul_bigrams(entry.source_text):
            by_bigram[bigram].append(entry)
    index = MemoryIndex(by_file=dict(by_file), by_token=dict(by_token), by_bigram=dict(by_bigram))
    MEMORY_INDEX_CACHE.clear()
    MEMORY_INDEX_CACHE[cache_key] = (len(memory), index)
    return index


def lexical_tokens(text: str) -> set[str]:
    return {match.group(0).lower() for match in TOKEN_RE.finditer(text)}


def hangul_bigrams(text: str) -> set[str]:
    chars = [ch for ch in text if "가" <= ch <= "힣"]
    return {chars[index] + chars[index + 1] for index in range(len(chars) - 1)}
