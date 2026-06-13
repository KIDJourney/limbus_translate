from __future__ import annotations

import csv
import json
import random
from dataclasses import asdict, dataclass, field
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

from .formatting import profile_text, same_multiset
from .glossary import GlossaryTerm, match_terms
from .json_paths import contains_cjk, contains_hangul, get_path, is_translatable_path, iter_text_nodes
from .providers import TranslationProvider, TranslationRequest, provider_metadata
from .scanner import classify_risk, load_json
from .translation_cache import (
    TranslationCacheEntry,
    TranslationRequestLogEntry,
    build_cache_key,
    digest_text,
    make_cache_entry,
    make_request_log_entry,
)


@dataclass(frozen=True)
class GoldTerm:
    source: str
    target: str
    note: str = ""


@dataclass(frozen=True)
class GoldCase:
    case_id: str
    source_text: str
    expected_text: str
    glossary: list[GoldTerm] = field(default_factory=list)
    context: dict[str, Any] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)
    note: str = ""


@dataclass(frozen=True)
class EvalResult:
    case_id: str
    source_text: str
    expected_text: str
    predicted_text: str
    exact_match: bool
    similarity: float
    passed: bool
    issues: list[str]
    tags: list[str]


@dataclass(frozen=True)
class EvalComparison:
    provider: str
    summary: dict[str, Any]
    results: list[EvalResult]


APPROVED_VALUES = {"1", "true", "yes", "y", "approved", "approve", "ok", "是", "通过", "已确认", "确认"}


def read_gold_cases(path: Path) -> list[GoldCase]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload.get("cases", payload) if isinstance(payload, dict) else payload
    cases: list[GoldCase] = []
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            continue
        cases.append(_case_from_row(row, fallback_id=f"case-{index + 1}"))
    return cases


def write_gold_cases(path: Path, cases: list[GoldCase]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"cases": [asdict(case) for case in cases]}
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_gold_review_pack(output_dir: Path, cases: list[GoldCase]) -> dict[str, int | str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    review_csv = output_dir / "review.csv"
    review_jsonl = output_dir / "review.jsonl"
    fieldnames = [
        "case_id",
        "approved",
        "expected_text",
        "revised_expected_text",
        "source_text",
        "tags",
        "risk",
        "relative_file",
        "json_path",
        "note",
        "reviewer_note",
    ]
    with review_csv.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for case in cases:
            writer.writerow(
                {
                    "case_id": case.case_id,
                    "approved": "",
                    "expected_text": case.expected_text,
                    "revised_expected_text": "",
                    "source_text": case.source_text,
                    "tags": " | ".join(case.tags),
                    "risk": case.context.get("risk", "") if isinstance(case.context, dict) else "",
                    "relative_file": case.context.get("relative_file", "") if isinstance(case.context, dict) else "",
                    "json_path": case.context.get("json_path", "") if isinstance(case.context, dict) else "",
                    "note": case.note,
                    "reviewer_note": "",
                }
            )
    with review_jsonl.open("w", encoding="utf-8") as handle:
        for case in cases:
            payload = asdict(case)
            payload["approved"] = ""
            payload["revised_expected_text"] = ""
            payload["reviewer_note"] = ""
            handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True))
            handle.write("\n")
    return {"selected": len(cases), "review_csv": str(review_csv), "review_jsonl": str(review_jsonl)}


def apply_gold_review_csv(review_path: Path, cases: list[GoldCase]) -> list[GoldCase]:
    by_id = {case.case_id: case for case in cases}
    with review_path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    curated: list[GoldCase] = []
    seen: set[str] = set()
    for row in rows:
        case_id = str(row.get("case_id", "")).strip()
        if not case_id or case_id in seen:
            continue
        source = by_id.get(case_id)
        if source is None:
            continue
        if not _is_approved(str(row.get("approved", ""))):
            continue
        revised = str(row.get("revised_expected_text", "")).strip()
        expected = revised or source.expected_text
        if not expected:
            continue
        reviewer_note = str(row.get("reviewer_note", "")).strip()
        note = source.note
        if reviewer_note:
            note = "; ".join(part for part in [source.note, f"reviewer={reviewer_note}"] if part)
        curated.append(
            GoldCase(
                case_id=source.case_id,
                source_text=source.source_text,
                expected_text=expected,
                glossary=source.glossary,
                context=source.context,
                tags=source.tags,
                note=note,
            )
        )
        seen.add(case_id)
    return curated


def sample_gold_cases(
    cases: list[GoldCase],
    *,
    limit: int | None = None,
    per_group: int | None = None,
    group_by: str = "tag",
    seed: int = 1,
) -> list[GoldCase]:
    if limit is None and per_group is None:
        return list(cases)
    if limit is not None and limit <= 0:
        return []
    if per_group is not None and per_group <= 0:
        return []

    buckets: dict[str, list[GoldCase]] = {}
    for case in cases:
        for label in _sample_group_labels(case, group_by):
            buckets.setdefault(label, []).append(case)

    rng = random.Random(seed)
    selected: list[GoldCase] = []
    seen: set[str] = set()
    for label in sorted(buckets):
        bucket = sorted(buckets[label], key=lambda case: case.case_id)
        rng.shuffle(bucket)
        taken = 0
        for case in bucket:
            if case.case_id in seen:
                continue
            selected.append(case)
            seen.add(case.case_id)
            taken += 1
            if per_group is not None and taken >= per_group:
                break
            if limit is not None and len(selected) >= limit:
                return selected

    if limit is not None and len(selected) < limit:
        remainder = [case for case in sorted(cases, key=lambda item: item.case_id) if case.case_id not in seen]
        rng.shuffle(remainder)
        selected.extend(remainder[: limit - len(selected)])
    return selected[:limit] if limit is not None else selected


def build_gold_cases(
    *,
    source_root: Path,
    target_root: Path,
    glossary: list[GlossaryTerm] | None = None,
    limit: int | None = None,
    min_source_length: int = 2,
    max_source_length: int = 500,
) -> list[GoldCase]:
    cases: list[GoldCase] = []
    seen: set[tuple[str, str]] = set()
    for source_file in sorted(source_root.rglob("*.json")):
        relative = source_file.relative_to(source_root).as_posix()
        target_file = target_root / relative
        if not target_file.exists():
            continue
        source_data = load_json(source_file)
        target_data = load_json(target_file)
        for node in iter_text_nodes(source_data):
            if not is_translatable_path(node.path):
                continue
            source_text = node.value.strip()
            if not contains_hangul(source_text):
                continue
            if len(source_text) < min_source_length or len(source_text) > max_source_length:
                continue
            try:
                target_text = get_path(target_data, node.path)
            except (KeyError, IndexError, ValueError, TypeError):
                continue
            if not isinstance(target_text, str):
                continue
            target_text = target_text.strip()
            if not _usable_reference_translation(source_text, target_text):
                continue
            key = (source_text, target_text)
            if key in seen:
                continue
            seen.add(key)
            risk = classify_risk(relative, node.path_id, source_text)
            terms = [
                GoldTerm(source=term.source, target=term.target, note=term.note)
                for term in match_terms(source_text, glossary or [])
                if term.target
            ]
            cases.append(
                GoldCase(
                    case_id=f"{relative}::{node.path_id}",
                    source_text=source_text,
                    expected_text=target_text,
                    glossary=terms,
                    context={"relative_file": relative, "json_path": node.path_id, "risk": risk},
                    tags=_gold_tags(relative, node.path_id, source_text, target_text, risk),
                )
            )
            if limit is not None and len(cases) >= limit:
                return cases
    return cases


def run_gold_evaluation(
    cases: list[GoldCase],
    provider: TranslationProvider,
    *,
    min_similarity: float = 0.75,
    provider_name: str = "",
    candidate_cache: dict[str, TranslationCacheEntry] | None = None,
    candidate_cache_updates: list[TranslationCacheEntry] | None = None,
    request_log: list[TranslationRequestLogEntry] | None = None,
) -> list[EvalResult]:
    results: list[EvalResult] = []
    for case in cases:
        request = build_eval_request(case)
        predicted = translate_eval_case(
            case,
            request,
            provider,
            provider_name=provider_name,
            candidate_cache=candidate_cache,
            candidate_cache_updates=candidate_cache_updates,
            request_log=request_log,
        )
        issues = evaluate_prediction(case, predicted, min_similarity=min_similarity)
        results.append(
            EvalResult(
                case_id=case.case_id,
                source_text=case.source_text,
                expected_text=case.expected_text,
                predicted_text=predicted,
                exact_match=_norm(predicted) == _norm(case.expected_text),
                similarity=round(text_similarity(predicted, case.expected_text), 4),
                passed=not issues,
                issues=issues,
                tags=case.tags,
            )
        )
    return results


def run_eval_comparison(
    cases: list[GoldCase],
    providers: list[tuple[str, TranslationProvider] | tuple[str, str, TranslationProvider]],
    *,
    min_similarity: float = 0.75,
    candidate_cache: dict[str, TranslationCacheEntry] | None = None,
    candidate_cache_updates: list[TranslationCacheEntry] | None = None,
    request_log: list[TranslationRequestLogEntry] | None = None,
) -> list[EvalComparison]:
    comparisons: list[EvalComparison] = []
    for provider_spec in providers:
        if len(provider_spec) == 2:
            label, provider = provider_spec
            provider_name = label
        else:
            label, provider_name, provider = provider_spec
        results = run_gold_evaluation(
            cases,
            provider,
            min_similarity=min_similarity,
            provider_name=provider_name,
            candidate_cache=candidate_cache,
            candidate_cache_updates=candidate_cache_updates,
            request_log=request_log,
        )
        comparisons.append(EvalComparison(provider=label, summary=summarize_eval(results), results=results))
    return comparisons


def build_eval_request(case: GoldCase) -> TranslationRequest:
    return TranslationRequest(
        source_text=case.source_text,
        glossary=[(term.source, term.target, term.note) for term in case.glossary],
        context=json.dumps(
            {
                "case_id": case.case_id,
                "tags": case.tags,
                "note": case.note,
                "gold_context": case.context,
            },
            ensure_ascii=False,
            sort_keys=True,
        ),
    )


def translate_eval_case(
    case: GoldCase,
    request: TranslationRequest,
    provider: TranslationProvider,
    *,
    provider_name: str = "",
    candidate_cache: dict[str, TranslationCacheEntry] | None = None,
    candidate_cache_updates: list[TranslationCacheEntry] | None = None,
    request_log: list[TranslationRequestLogEntry] | None = None,
) -> str:
    provider_key = provider_name or provider.__class__.__name__
    source_hash = digest_text(case.source_text)
    cache_key, context_hash, glossary_hash = build_cache_key(
        provider=provider_key,
        source_hash=source_hash,
        context=request.context,
        glossary=request.glossary,
    )
    cached = (candidate_cache or {}).get(cache_key)
    if cached is not None:
        return cached.target_text
    relative_file = str(case.context.get("relative_file", "")) if isinstance(case.context, dict) else ""
    json_path = str(case.context.get("json_path", "")) if isinstance(case.context, dict) else ""
    translated = provider.translate(request)
    if request_log is not None:
        metadata = provider_metadata(provider)
        request_log.append(
            make_request_log_entry(
                cache_key=cache_key,
                provider=provider_key,
                source_hash=source_hash,
                context_hash=context_hash,
                glossary_hash=glossary_hash,
                unit_id=case.case_id,
                stable_key=case.case_id,
                relative_file=relative_file,
                json_path=json_path,
                source_text=case.source_text,
                glossary=request.glossary,
                context=request.context,
                target_text=translated,
                response_model=str(metadata.get("response_model", "")),
                response_id=str(metadata.get("response_id", "")),
                usage=metadata.get("usage", {}) if isinstance(metadata.get("usage", {}), dict) else {},
            )
        )
    if candidate_cache_updates is not None:
        entry = make_cache_entry(
            cache_key=cache_key,
            provider=provider_key,
            source_hash=source_hash,
            context_hash=context_hash,
            glossary_hash=glossary_hash,
            unit_id=case.case_id,
            stable_key=case.case_id,
            relative_file=relative_file,
            json_path=json_path,
            source_text=case.source_text,
            target_text=translated,
        )
        candidate_cache_updates.append(entry)
        if candidate_cache is not None:
            candidate_cache[cache_key] = entry
    return translated


def evaluate_prediction(case: GoldCase, predicted_text: str, *, min_similarity: float) -> list[str]:
    issues: list[str] = []
    similarity = text_similarity(predicted_text, case.expected_text)
    if similarity < min_similarity:
        issues.append("similarity_below_threshold")
    expected_profile = profile_text(case.expected_text)
    predicted_profile = profile_text(predicted_text)
    if not same_multiset(expected_profile.placeholders, predicted_profile.placeholders):
        issues.append("placeholder_mismatch")
    if not same_multiset(expected_profile.tags, predicted_profile.tags):
        issues.append("tag_mismatch")
    if not same_multiset(expected_profile.numbers, predicted_profile.numbers):
        issues.append("number_mismatch")
    if expected_profile.line_breaks != predicted_profile.line_breaks:
        issues.append("line_break_mismatch")
    for term in case.glossary:
        if term.source and term.source in case.source_text and term.target and term.target not in predicted_text:
            issues.append(f"term_missing:{term.source}")
    return issues


def summarize_eval(results: list[EvalResult]) -> dict[str, Any]:
    total = len(results)
    passed = sum(1 for result in results if result.passed)
    issue_counts: dict[str, int] = {}
    tag_counts: dict[str, int] = {}
    for result in results:
        for issue in result.issues:
            issue_counts[issue] = issue_counts.get(issue, 0) + 1
        for tag in result.tags:
            tag_counts[tag] = tag_counts.get(tag, 0) + 1
    avg_similarity = sum(result.similarity for result in results) / total if total else 0.0
    return {
        "total": total,
        "passed": passed,
        "failed": total - passed,
        "pass_rate": round(passed / total, 4) if total else 0.0,
        "avg_similarity": round(avg_similarity, 4),
        "by_issue": dict(sorted(issue_counts.items())),
        "by_tag": dict(sorted(tag_counts.items())),
    }


def write_eval_report(path: Path, results: list[EvalResult], usage_summary: dict[str, Any] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    summary = summarize_eval(results)
    if usage_summary is not None:
        summary["usage"] = usage_summary
    payload = {"summary": summary, "results": [asdict(result) for result in results]}
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def summarize_eval_comparison(comparisons: list[EvalComparison]) -> dict[str, Any]:
    rankings = sorted(
        (
            {
                "provider": comparison.provider,
                "total": comparison.summary["total"],
                "pass_rate": comparison.summary["pass_rate"],
                "avg_similarity": comparison.summary["avg_similarity"],
                "failed": comparison.summary["failed"],
            }
            for comparison in comparisons
        ),
        key=lambda row: (-float(row["pass_rate"]), -float(row["avg_similarity"]), str(row["provider"])),
    )
    return {"providers": len(comparisons), "rankings": rankings}


def write_eval_comparison_report(
    path: Path,
    comparisons: list[EvalComparison],
    usage_summary: dict[str, Any] | None = None,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    summary = summarize_eval_comparison(comparisons)
    if usage_summary is not None:
        summary["usage"] = usage_summary
    payload = {
        "summary": summary,
        "providers": [
            {
                "provider": comparison.provider,
                "summary": comparison.summary,
                "results": [asdict(result) for result in comparison.results],
            }
            for comparison in comparisons
        ],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def text_similarity(left: str, right: str) -> float:
    return SequenceMatcher(None, _norm(left), _norm(right)).ratio()


def _usable_reference_translation(source_text: str, target_text: str) -> bool:
    if not target_text:
        return False
    if target_text == source_text:
        return False
    if contains_hangul(target_text):
        return False
    if not contains_cjk(target_text):
        return False
    return True


def _gold_tags(relative_file: str, json_path: str, source_text: str, target_text: str, risk: str) -> list[str]:
    tags = [risk]
    key = json_path.split(".")[-1]
    if relative_file.startswith("StoryData/") or key in {"content", "dlg"}:
        tags.append("story")
    if key in {"name", "title", "teller"}:
        tags.append("name")
    if profile_text(source_text).placeholders or profile_text(target_text).placeholders:
        tags.append("placeholder")
    if profile_text(source_text).tags or profile_text(target_text).tags:
        tags.append("format")
    return tags


def _sample_group_labels(case: GoldCase, group_by: str) -> list[str]:
    if group_by == "tag":
        return case.tags or ["untagged"]
    if group_by == "risk":
        risk = case.context.get("risk") if isinstance(case.context, dict) else None
        if risk:
            return [str(risk)]
        for tag in case.tags:
            if tag in {"low", "medium", "high", "internal"}:
                return [tag]
        return ["unknown"]
    if group_by == "file":
        relative = case.context.get("relative_file") if isinstance(case.context, dict) else None
        return [str(relative or "unknown")]
    raise ValueError(f"unknown gold sample group: {group_by}")


def _is_approved(value: str) -> bool:
    return value.strip().lower() in APPROVED_VALUES


def _case_from_row(row: dict[str, Any], *, fallback_id: str) -> GoldCase:
    glossary_rows = row.get("glossary", [])
    glossary = [
        GoldTerm(
            source=str(term.get("source", "")),
            target=str(term.get("target", "")),
            note=str(term.get("note", "")),
        )
        for term in glossary_rows
        if isinstance(term, dict)
    ]
    tags = row.get("tags", [])
    return GoldCase(
        case_id=str(row.get("case_id") or row.get("id") or fallback_id),
        source_text=str(row.get("source_text") or row.get("source") or ""),
        expected_text=str(row.get("expected_text") or row.get("expected") or row.get("target") or ""),
        glossary=glossary,
        context=dict(row.get("context", {})) if isinstance(row.get("context", {}), dict) else {},
        tags=[str(tag) for tag in tags] if isinstance(tags, list) else [],
        note=str(row.get("note", "")),
    )


def _norm(value: str) -> str:
    return " ".join(value.strip().split())
