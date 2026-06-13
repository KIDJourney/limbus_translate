import csv
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from limbus_translate.evaluation import (
    GoldCase,
    GoldTerm,
    apply_gold_review_csv,
    build_gold_cases,
    read_gold_cases,
    run_eval_comparison,
    run_gold_evaluation,
    sample_gold_cases,
    summarize_eval_comparison,
    summarize_eval,
    write_eval_comparison_report,
    write_eval_report,
    write_gold_cases,
    write_gold_review_pack,
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


def make_gold_case(case_id: str, tags: list[str], risk: str = "medium"):
    return GoldCase(
        case_id=case_id,
        source_text=f"{case_id} 원문",
        expected_text=f"{case_id} 译文",
        context={"risk": risk, "relative_file": f"{case_id}.json"},
        tags=tags,
    )


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


def test_eval_comparison_ranks_providers() -> None:
    cases = read_gold_cases(Path("tests/fixtures/gold-set.json"))

    comparisons = run_eval_comparison(cases, [("gold", GoldProvider()), ("bad", BadProvider())], min_similarity=0.9)
    summary = summarize_eval_comparison(comparisons)
    with TemporaryDirectory() as tmp:
        path = Path(tmp) / "eval-compare-report.json"
        write_eval_comparison_report(path, comparisons)
        text = path.read_text(encoding="utf-8")

    assert summary["providers"] == 2
    assert summary["rankings"][0]["provider"] == "gold"
    assert summary["rankings"][0]["pass_rate"] == 1.0
    assert summary["rankings"][1]["provider"] == "bad"
    assert '"providers"' in text
    assert '"rankings"' in text


def test_sample_gold_cases_is_stratified_and_repeatable() -> None:
    cases = [
        make_gold_case("story-1", ["story"], risk="medium"),
        make_gold_case("story-2", ["story"], risk="medium"),
        make_gold_case("story-3", ["story"], risk="medium"),
        make_gold_case("name-1", ["name"], risk="low"),
        make_gold_case("name-2", ["name"], risk="low"),
        make_gold_case("format-1", ["format"], risk="high"),
    ]

    first = sample_gold_cases(cases, per_group=1, group_by="tag", seed=7)
    second = sample_gold_cases(cases, per_group=1, group_by="tag", seed=7)
    by_id = {case.case_id for case in first}
    by_risk = sample_gold_cases(cases, per_group=1, group_by="risk", seed=7)

    assert [case.case_id for case in first] == [case.case_id for case in second]
    assert len(first) == 3
    assert any(case_id.startswith("story-") for case_id in by_id)
    assert any(case_id.startswith("name-") for case_id in by_id)
    assert "format-1" in by_id
    assert len(by_risk) == 3
    assert {case.context["risk"] for case in by_risk} == {"low", "medium", "high"}


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


def test_write_gold_review_pack_exports_review_files() -> None:
    cases = [
        GoldCase(
            case_id="story-1",
            source_text="단테가 말했다.",
            expected_text="但丁说道。",
            glossary=[GoldTerm(source="단테", target="但丁", note="name")],
            context={"relative_file": "StoryData/A.json", "json_path": "dataList[0].content", "risk": "high"},
            tags=["high", "story"],
            note="sample note",
        )
    ]
    with TemporaryDirectory() as tmp:
        summary = write_gold_review_pack(Path(tmp), cases)
        with (Path(tmp) / "review.csv").open("r", encoding="utf-8-sig", newline="") as handle:
            review_rows = list(csv.DictReader(handle))
        jsonl_rows = [json.loads(line) for line in (Path(tmp) / "review.jsonl").read_text(encoding="utf-8").splitlines()]

    assert summary["selected"] == 1
    assert review_rows[0]["case_id"] == "story-1"
    assert review_rows[0]["approved"] == ""
    assert review_rows[0]["expected_text"] == "但丁说道。"
    assert review_rows[0]["tags"] == "high | story"
    assert review_rows[0]["relative_file"] == "StoryData/A.json"
    assert review_rows[0]["json_path"] == "dataList[0].content"
    assert jsonl_rows[0]["glossary"][0]["target"] == "但丁"
    assert jsonl_rows[0]["context"]["risk"] == "high"


def test_apply_gold_review_csv_preserves_original_case_structure() -> None:
    cases = [
        GoldCase(
            case_id="story-1",
            source_text="단테가 말했다.",
            expected_text="但丁说道。",
            glossary=[GoldTerm(source="단테", target="但丁", note="name")],
            context={"relative_file": "StoryData/A.json", "json_path": "dataList[0].content", "risk": "high"},
            tags=["high", "story"],
        ),
        make_gold_case("story-2", ["story"]),
        make_gold_case("story-3", ["story"]),
    ]
    with TemporaryDirectory() as tmp:
        path = Path(tmp) / "review.csv"
        with path.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=["case_id", "approved", "expected_text", "revised_expected_text", "reviewer_note"],
            )
            writer.writeheader()
            writer.writerow(
                {
                    "case_id": "story-1",
                    "approved": "yes",
                    "expected_text": "但丁说道。",
                    "revised_expected_text": "但丁开口了。",
                    "reviewer_note": "tone fixed",
                }
            )
            writer.writerow(
                {
                    "case_id": "story-2",
                    "approved": "",
                    "expected_text": "story-2 译文",
                    "revised_expected_text": "",
                    "reviewer_note": "pending",
                }
            )
            writer.writerow(
                {
                    "case_id": "story-3",
                    "approved": "通过",
                    "expected_text": "story-3 译文",
                    "revised_expected_text": "",
                    "reviewer_note": "",
                }
            )
            writer.writerow(
                {
                    "case_id": "unknown",
                    "approved": "yes",
                    "expected_text": "unknown",
                    "revised_expected_text": "",
                    "reviewer_note": "",
                }
            )
        curated = apply_gold_review_csv(path, cases)

    assert [case.case_id for case in curated] == ["story-1", "story-3"]
    assert curated[0].expected_text == "但丁开口了。"
    assert curated[0].glossary[0].target == "但丁"
    assert curated[0].context["relative_file"] == "StoryData/A.json"
    assert curated[0].tags == ["high", "story"]
    assert curated[0].note == "reviewer=tone fixed"
    assert curated[1].expected_text == "story-3 译文"
