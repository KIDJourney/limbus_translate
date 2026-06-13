from limbus_translate.qa import check_pair, summarize_issues
from limbus_translate.scanner import TranslationUnit


def make_unit(source_text: str = "{0} 피해량 10% 증가") -> TranslationUnit:
    return TranslationUnit(
        unit_id="u1",
        relative_file="Sample.json",
        json_path="dataList.0.desc",
        source_text=source_text,
        target_text="",
        reason="missing_target_text",
        source_hash="hash",
        target_hash=None,
        placeholders=["{0}"],
        tags=[],
        numbers=["0", "10%"],
        line_breaks=0,
        risk="medium",
    )


def test_qa_detects_placeholder_mismatch() -> None:
    unit = make_unit()
    issues = check_pair(unit, "伤害提高 10%", [])
    issue = next(issue for issue in issues if issue.code == "placeholder_mismatch")
    assert issue.category == "format"


def test_qa_detects_traditional_and_length() -> None:
    unit = TranslationUnit(
        unit_id="u1",
        relative_file="Sample.json",
        json_path="dataList.0.desc",
        source_text="짧지 않은 원문입니다.",
        target_text="",
        reason="missing_target_text",
        source_hash="hash",
        target_hash=None,
        placeholders=[],
        tags=[],
        numbers=[],
        line_breaks=0,
        risk="medium",
    )
    issues = check_pair(unit, "這裡" + "很长" * 80, [])
    codes = {issue.code for issue in issues}
    assert "traditional_chinese" in codes
    assert "length_ratio_high" in codes
    assert "line_too_long" in codes
    summary = summarize_issues(issues)
    assert summary["by_category"]["locale_convention"] == 1
    assert summary["by_category"]["design"] >= 2
    assert summary["by_code"]["traditional_chinese"] == 1
