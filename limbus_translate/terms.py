from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path

from .glossary import GlossaryTerm, normalize_text
from .scanner import TranslationUnit


HANGUL_PHRASE_RE = re.compile(r"[가-힣][가-힣A-Za-z0-9 .·'’:\-]{1,30}[가-힣A-Za-z0-9]")
STOPWORDS = {
    "사용 안하는 텍스트",
    "표시용",
    "더미",
}


@dataclass(frozen=True)
class TermCandidate:
    source: str
    count: int
    contexts: list[str]
    sample_text: str
    reason: str


def known_sources(glossary: list[GlossaryTerm]) -> set[str]:
    values: set[str] = set()
    for term in glossary:
        values.add(normalize_text(term.source))
        for variant in term.variants:
            values.add(normalize_text(variant))
    return values


def candidate_reason(term: str) -> str:
    if any(ch.isdigit() for ch in term):
        return "contains_number"
    if any(mark in term for mark in ["·", "'", "’", "-"]):
        return "marked_name"
    if len(term) >= 8:
        return "long_phrase"
    return "hangul_phrase"


def extract_term_candidates(
    units: list[TranslationUnit],
    glossary: list[GlossaryTerm],
    *,
    min_count: int = 1,
    max_contexts: int = 5,
) -> list[TermCandidate]:
    known = known_sources(glossary)
    buckets: dict[str, list[TranslationUnit]] = {}
    display: dict[str, str] = {}
    for unit in units:
        for match in HANGUL_PHRASE_RE.findall(unit.source_text):
            phrase = " ".join(match.strip(" .,:;!?()[]{}<>\"'“”‘’").split())
            if len(phrase) < 2 or phrase in STOPWORDS:
                continue
            key = normalize_text(phrase)
            if not key or key in known:
                continue
            buckets.setdefault(key, []).append(unit)
            display.setdefault(key, phrase)
    candidates: list[TermCandidate] = []
    for key, matched_units in buckets.items():
        if len(matched_units) < min_count:
            continue
        phrase = display[key]
        contexts = [f"{unit.relative_file}::{unit.json_path}" for unit in matched_units[:max_contexts]]
        candidates.append(
            TermCandidate(
                source=phrase,
                count=len(matched_units),
                contexts=contexts,
                sample_text=matched_units[0].source_text,
                reason=candidate_reason(phrase),
            )
        )
    candidates.sort(key=lambda item: (-item.count, item.source))
    return candidates


def write_candidates(path: Path, candidates: list[TermCandidate]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump([asdict(candidate) for candidate in candidates], handle, ensure_ascii=False, indent=2)
        handle.write("\n")
