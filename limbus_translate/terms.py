from __future__ import annotations

import csv
import json
import os
import re
import time
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
APPROVED_VALUES = {"1", "true", "yes", "y", "approved", "approve", "ok", "是", "通过", "已确认", "确认"}


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


def _term_cache_key(source: str) -> str:
    return normalize_text(source)


def _reuse_refined_term(candidate: TermCandidate, cached: RefinedTerm) -> RefinedTerm:
    return RefinedTerm(
        source=candidate.source,
        decision=cached.decision,
        suggested_target=cached.suggested_target,
        note=cached.note,
        confidence=cached.confidence,
        contexts=candidate.contexts,
        provider=cached.provider,
        count=candidate.count,
        sample_text=candidate.sample_text,
        reason=candidate.reason,
        raw=cached.raw,
    )


def refine_candidates_with_cache(
    candidates: list[TermCandidate],
    refiner: TermRefiner,
    cached_terms: list[RefinedTerm],
) -> tuple[list[RefinedTerm], list[RefinedTerm], int]:
    cached_by_source = {_term_cache_key(term.source): term for term in cached_terms if _term_cache_key(term.source)}
    missing_candidates: list[TermCandidate] = []
    for candidate in candidates:
        if _term_cache_key(candidate.source) not in cached_by_source:
            missing_candidates.append(candidate)

    new_terms = refiner.refine(missing_candidates)
    new_by_source = {_term_cache_key(term.source): term for term in new_terms}
    refined: list[RefinedTerm] = []
    reused = 0
    for candidate in candidates:
        key = _term_cache_key(candidate.source)
        cached = cached_by_source.get(key)
        if cached is not None:
            refined.append(_reuse_refined_term(candidate, cached))
            reused += 1
            continue
        refined.append(new_by_source[key])
    return refined, new_terms, reused


def merge_refined_term_cache(existing: list[RefinedTerm], updates: list[RefinedTerm]) -> list[RefinedTerm]:
    merged = {_term_cache_key(term.source): term for term in existing if _term_cache_key(term.source)}
    for term in updates:
        key = _term_cache_key(term.source)
        if key:
            merged[key] = term
    return sorted(merged.values(), key=lambda term: normalize_text(term.source))


def promote_refined_terms(
    refined_terms: list[RefinedTerm],
    *,
    provider: str = "local-refined",
    source_lang: str = "ko",
    target_lang: str = "zh-cn",
    min_confidence: float = 0.0,
) -> list[GlossaryTerm]:
    fetched_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    promoted: list[GlossaryTerm] = []
    for index, term in enumerate(refined_terms):
        if term.decision != "term":
            continue
        if term.confidence < min_confidence:
            continue
        if not term.source.strip() or not term.suggested_target.strip():
            continue
        note_parts = [part for part in [term.note, f"source={term.provider}", f"reason={term.reason}"] if part]
        promoted.append(
            GlossaryTerm(
                provider=provider,
                project_id=None,
                term_id=index,
                source_lang=source_lang,
                target_lang=target_lang,
                source=term.source,
                target=term.suggested_target,
                note="; ".join(note_parts),
                part_of_speech="",
                variants=[],
                case_sensitive=False,
                created_at=None,
                updated_at=fetched_at,
                raw=asdict(term),
                fetched_at=fetched_at,
            )
        )
    return promoted


def is_approved(value: str) -> bool:
    return value.strip().lower() in APPROVED_VALUES


def glossary_terms_from_review_csv(
    path: Path,
    *,
    provider: str = "local-reviewed",
    source_lang: str = "ko",
    target_lang: str = "zh-cn",
) -> list[GlossaryTerm]:
    fetched_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    terms: list[GlossaryTerm] = []
    for index, row in enumerate(rows):
        source = str(row.get("source", "")).strip()
        target = str(row.get("target", "")).strip()
        if not source or not target or not is_approved(str(row.get("approved", ""))):
            continue
        note_parts = [
            str(row.get("note", "")).strip(),
            f"review_decision={str(row.get('decision', '')).strip()}",
            f"source_provider={str(row.get('provider', '')).strip()}",
            f"reason={str(row.get('reason', '')).strip()}",
        ]
        terms.append(
            GlossaryTerm(
                provider=provider,
                project_id=None,
                term_id=index,
                source_lang=source_lang,
                target_lang=target_lang,
                source=source,
                target=target,
                note="; ".join(part for part in note_parts if part and not part.endswith("=")),
                part_of_speech="",
                variants=[],
                case_sensitive=False,
                created_at=None,
                updated_at=fetched_at,
                raw=dict(row),
                fetched_at=fetched_at,
            )
        )
    return terms


def reviewable_terms(
    refined_terms: list[RefinedTerm],
    *,
    include_not_term: bool = False,
    min_confidence: float = 0.0,
) -> list[RefinedTerm]:
    selected: list[RefinedTerm] = []
    for term in refined_terms:
        if term.confidence < min_confidence:
            continue
        if term.decision == "not_term" and not include_not_term:
            continue
        selected.append(term)
    order = {"term": 0, "needs_review": 1, "not_term": 2}
    selected.sort(key=lambda term: (order.get(term.decision, 99), -term.confidence, term.source))
    return selected


def write_term_review_pack(
    output_dir: Path,
    refined_terms: list[RefinedTerm],
    *,
    include_not_term: bool = False,
    min_confidence: float = 0.0,
) -> dict[str, int | str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    selected = reviewable_terms(refined_terms, include_not_term=include_not_term, min_confidence=min_confidence)
    review_csv = output_dir / "review.csv"
    review_jsonl = output_dir / "review.jsonl"
    paratranz_csv = output_dir / "paratranz-import.csv"

    fieldnames = [
        "source",
        "target",
        "approved",
        "decision",
        "confidence",
        "provider",
        "count",
        "reason",
        "note",
        "contexts",
        "sample_text",
    ]
    with review_csv.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for term in selected:
            writer.writerow(
                {
                    "source": term.source,
                    "target": term.suggested_target,
                    "approved": "",
                    "decision": term.decision,
                    "confidence": f"{term.confidence:.2f}",
                    "provider": term.provider,
                    "count": term.count,
                    "reason": term.reason,
                    "note": term.note,
                    "contexts": " | ".join(term.contexts),
                    "sample_text": term.sample_text,
                }
            )

    with review_jsonl.open("w", encoding="utf-8") as handle:
        for term in selected:
            payload = asdict(term)
            payload["approved"] = ""
            handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True))
            handle.write("\n")

    importable = [term for term in selected if term.decision == "term" and term.suggested_target.strip()]
    with paratranz_csv.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["term", "translation", "note"])
        writer.writeheader()
        for term in importable:
            note_parts = [part for part in [term.note, f"provider={term.provider}", f"reason={term.reason}"] if part]
            writer.writerow({"term": term.source, "translation": term.suggested_target, "note": "; ".join(note_parts)})

    return {
        "selected": len(selected),
        "paratranz_candidates": len(importable),
        "review_csv": str(review_csv),
        "review_jsonl": str(review_jsonl),
        "paratranz_csv": str(paratranz_csv),
    }


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
