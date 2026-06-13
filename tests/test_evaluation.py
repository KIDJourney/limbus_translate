from pathlib import Path
from tempfile import TemporaryDirectory

from limbus_translate.evaluation import (
    build_gold_cases,
    read_gold_cases,
    run_gold_evaluation,
    summarize_eval,
    write_eval_report,
    write_gold_cases,
)
from limbus_translate.glossary import GlossaryTerm
from limbus_translate.providers import TranslationRequest


def make_term(source: str, target: str) -> GlossaryTerm:
    return GlossaryTerm(
        provider="test",
        project_id=None,
        term_id=None,
        source_lang="ko",
        target_lang="zh-cn",
        source=source,
        target=target,
        note="approved",
        part_of_speech="noun",
        variants=[],
        case_sensitive=False,
        created_at=None,
        updated_at=None,
        raw={},
        fetched_at="2026-06-13T00:00:00Z",
    )


class GoldProvider:
    def translate(self, request: TranslationRequest) -> str:
        if "단테" in request.source_text:
            return "但丁开始了战斗。"
        if "{0}" in request.source_text:
            return "<color=#ff0000>{0}</color> 受到了伤害。"
        return request.source_text


class BadProvider:
    def translate(self, request: TranslationRequest) -> str:
        return "错误译文"


def test_gold_evaluation_passes_matching_provider() -> None:
    cases = read_gold_cases(Path("tests/fixtures/gold-set.json"))

    results = run_gold_evaluation(cases, GoldProvider())
    summary = summarize_eval(results)

    assert summary["total"] == 2
    assert summary["passed"] == 2
    assert summary["pass_rate"] == 1.0
    assert results[0].exact_match


def test_gold_evaluation_reports_quality_issues() -> None:
    cases = read_gold_cases(Path("tests/fixtures/gold-set.json"))

    results = run_gold_evaluation(cases, BadProvider(), min_similarity=0.9)
    summary = summarize_eval(results)

    assert summary["passed"] == 0
    assert summary["by_issue"]["similarity_below_threshold"] == 2
    assert "term_missing:단테" in results[0].issues
    assert "placeholder_mismatch" in results[1].issues
    assert "tag_mismatch" in results[1].issues


def test_eval_report_roundtrip() -> None:
    cases = read_gold_cases(Path("tests/fixtures/gold-set.json"))
    results = run_gold_evaluation(cases, GoldProvider())
    with TemporaryDirectory() as tmp:
        path = Path(tmp) / "eval-report.json"
        write_eval_report(path, results)
        text = path.read_text(encoding="utf-8")

    assert '"summary"' in text
    assert '"results"' in text


def test_build_gold_cases_from_reference_tree() -> None:
    cases = build_gold_cases(
        source_root=Path("tests/fixtures/localize/KR"),
        target_root=Path("tests/fixtures/localize/LLC_zh-CN"),
        glossary=[make_term("단테", "但丁")],
    )

    by_source = {case.source_text: case for case in cases}
    assert by_source["단테"].expected_text == "但丁"
    assert by_source["단테"].glossary[0].target == "但丁"
    assert by_source["단테"].context["relative_file"] == "Sample.json"
    assert "name" in by_source["단테"].tags
    assert "안아준다." in by_source
    assert "사용 안하는 텍스트" not in by_source


def test_write_gold_cases_roundtrip() -> None:
    cases = build_gold_cases(
        source_root=Path("tests/fixtures/localize/KR"),
        target_root=Path("tests/fixtures/localize/LLC_zh-CN"),
        limit=1,
    )
    with TemporaryDirectory() as tmp:
        path = Path(tmp) / "gold.json"
        write_gold_cases(path, cases)
        loaded = read_gold_cases(path)

    assert loaded == cases
