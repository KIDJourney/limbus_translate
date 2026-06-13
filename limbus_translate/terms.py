from __future__ import annotations

import json
import os
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Protocol

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


@dataclass(frozen=True)
class RefinedTerm:
    source: str
    decision: str
    suggested_target: str
    note: str
    confidence: float
    contexts: list[str]
    provider: str
    count: int
    sample_text: str
    reason: str
    raw: dict[str, Any]


class TermRefiner(Protocol):
    name: str

    def refine(self, candidates: list[TermCandidate]) -> list[RefinedTerm]:
        ...


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


def read_candidates(path: Path) -> list[TermCandidate]:
    rows = json.loads(path.read_text(encoding="utf-8"))
    return [TermCandidate(**row) for row in rows]


def write_refined_terms(path: Path, terms: list[RefinedTerm]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump([asdict(term) for term in terms], handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def read_refined_terms(path: Path) -> list[RefinedTerm]:
    rows = json.loads(path.read_text(encoding="utf-8"))
    return [RefinedTerm(**row) for row in rows]


class RulesTermRefiner:
    name = "rules"

    def refine(self, candidates: list[TermCandidate]) -> list[RefinedTerm]:
        return [self._refine_one(candidate) for candidate in candidates]

    def _refine_one(self, candidate: TermCandidate) -> RefinedTerm:
        source = candidate.source
        compact_len = len(source.replace(" ", ""))
        has_sentence_ending = source.endswith(("다", "요", "죠", "까", "네"))
        has_space = " " in source

        if candidate.reason == "long_phrase" and (has_space or compact_len >= 14 or has_sentence_ending):
            decision = "not_term"
            confidence = 0.72
            note = "Looks more like a phrase or sentence than a reusable glossary term."
        elif candidate.reason in {"marked_name", "contains_number"}:
            decision = "needs_review"
            confidence = 0.74
            note = "Looks like a proper noun or named expression; needs an approved Chinese rendering."
        elif candidate.count >= 2 and compact_len <= 12:
            decision = "term"
            confidence = 0.7
            note = "Repeated short Hangul expression; likely worth keeping in the local term cache."
        else:
            decision = "needs_review"
            confidence = 0.58
            note = "Short Hangul expression; keep it for LLM or human terminology review."

        return RefinedTerm(
            source=source,
            decision=decision,
            suggested_target="",
            note=note,
            confidence=confidence,
            contexts=candidate.contexts,
            provider=self.name,
            count=candidate.count,
            sample_text=candidate.sample_text,
            reason=candidate.reason,
            raw={},
        )


class OpenAITermRefiner:
    name = "openai"

    def __init__(self, model: str | None = None) -> None:
        self.model = model or os.environ.get("OPENAI_TERM_MODEL") or os.environ.get("OPENAI_TRANSLATION_MODEL", "gpt-4.1")

    def refine(self, candidates: list[TermCandidate]) -> list[RefinedTerm]:
        if not candidates:
            return []
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError("OpenAI term refiner requires `pip install '.[openai]'`.") from exc

        client = OpenAI()
        payload = [
            {
                "source": candidate.source,
                "count": candidate.count,
                "reason": candidate.reason,
                "sample_text": candidate.sample_text,
                "contexts": candidate.contexts,
            }
            for candidate in candidates
        ]
        prompt = {
            "task": "Refine Korean Limbus Company term candidates for a Simplified Chinese localization glossary.",
            "decisions": {
                "term": "Reusable glossary term with a confident Chinese rendering.",
                "not_term": "Ordinary sentence fragment, grammar residue, or not useful as a glossary term.",
                "needs_review": "Probably important but Chinese rendering needs human confirmation.",
            },
            "requirements": [
                "Return only JSON.",
                "Return one object per input candidate.",
                "Use decision values exactly: term, not_term, needs_review.",
                "For suggested_target, use Simplified Chinese when confident; otherwise use an empty string.",
                "Preserve each source string exactly.",
            ],
            "candidates": payload,
        }
        response = client.responses.create(
            model=self.model,
            input=[
                {
                    "role": "system",
                    "content": "You are a Korean-to-Simplified-Chinese game localization terminology editor.",
                },
                {"role": "user", "content": json.dumps(prompt, ensure_ascii=False)},
            ],
        )
        raw_rows = json.loads(response.output_text)
        if not isinstance(raw_rows, list):
            raise ValueError("OpenAI term refiner returned non-list JSON.")
        by_source = {candidate.source: candidate for candidate in candidates}
        refined: list[RefinedTerm] = []
        for row in raw_rows:
            if not isinstance(row, dict):
                raise ValueError("OpenAI term refiner returned a non-object row.")
            source = str(row.get("source", ""))
            candidate = by_source.get(source)
            if candidate is None:
                raise ValueError(f"OpenAI term refiner returned unknown source: {source}")
            decision = str(row.get("decision", "needs_review"))
            if decision not in {"term", "not_term", "needs_review"}:
                decision = "needs_review"
            refined.append(
                RefinedTerm(
                    source=source,
                    decision=decision,
                    suggested_target=str(row.get("suggested_target", "")),
                    note=str(row.get("note", "")),
                    confidence=_bounded_confidence(row.get("confidence", 0.0)),
                    contexts=candidate.contexts,
                    provider=self.name,
                    count=candidate.count,
                    sample_text=candidate.sample_text,
                    reason=candidate.reason,
                    raw=row,
                )
            )
        return refined


def _bounded_confidence(value: object) -> float:
    try:
        confidence = float(value)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(1.0, confidence))


def get_term_refiner(name: str) -> TermRefiner:
    if name == "rules":
        return RulesTermRefiner()
    if name == "openai":
        return OpenAITermRefiner()
    raise ValueError(f"unknown term refiner: {name}")
