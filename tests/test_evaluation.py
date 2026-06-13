from pathlib import Path
from tempfile import TemporaryDirectory

from limbus_translate.evaluation import read_gold_cases, run_gold_evaluation, summarize_eval, write_eval_report
from limbus_translate.providers import TranslationRequest


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
