from limbus_translate.qa import check_pair
from limbus_translate.scanner import TranslationUnit


def test_qa_detects_placeholder_mismatch() -> None:
    unit = TranslationUnit(
        unit_id="u1",
        relative_file="Sample.json",
        json_path="dataList.0.desc",
        source_text="{0} 피해량 10% 증가",
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
    issues = check_pair(unit, "伤害提高 10%", [])
    assert any(issue.code == "placeholder_mismatch" for issue in issues)
