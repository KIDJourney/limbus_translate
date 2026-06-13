from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

from .formatting import profile_text, same_multiset
from .glossary import GlossaryTerm, match_terms
from .json_paths import contains_cjk, contains_hangul, get_path, is_translatable_path, iter_text_nodes
from .providers import TranslationProvider, TranslationRequest
from .scanner import classify_risk, load_json


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
) -> list[EvalResult]:
    results: list[EvalResult] = []
    for case in cases:
        request = TranslationRequest(
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
        predicted = provider.translate(request)
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
    providers: list[tuple[str, TranslationProvider]],
    *,
    min_similarity: float = 0.75,
) -> list[EvalComparison]:
    comparisons: list[EvalComparison] = []
    for label, provider in providers:
        results = run_gold_evaluation(cases, provider, min_similarity=min_similarity)
        comparisons.append(EvalComparison(provider=label, summary=summarize_eval(results), results=results))
    return comparisons


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


def write_eval_report(path: Path, results: list[EvalResult]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"summary": summarize_eval(results), "results": [asdict(result) for result in results]}
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


def write_eval_comparison_report(path: Path, comparisons: list[EvalComparison]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "summary": summarize_eval_comparison(comparisons),
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
