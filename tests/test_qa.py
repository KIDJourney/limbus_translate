import json
from pathlib import Path
from tempfile import TemporaryDirectory

from limbus_translate.qa import check_pair, display_width, read_length_policy, summarize_issues
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


def test_qa_uses_path_specific_length_policy() -> None:
    with TemporaryDirectory() as tmp:
        path = Path(tmp) / "length-policy.json"
        path.write_text(
            json.dumps(
                {
                    "default": {"max_line_length": 80, "max_ratio": 2.2, "min_ratio": 0.25},
                    "rules": [
                        {
                            "name": "compact story content",
                            "relative_file_prefix": "StoryData/",
                            "json_path_suffix": ".content",
                            "max_line_length": 12,
                            "max_ratio": 1.5,
                            "min_ratio": 0.2,
                            "min_source_length": 1,
                        }
                    ],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        policy = read_length_policy(path)

    unit = TranslationUnit(
        unit_id="u1",
        relative_file="StoryData/Sample.json",
        json_path="dataList.0.content",
        source_text="짧은 문장",
        target_text="",
        reason="missing_target_text",
        source_hash="hash",
        target_hash=None,
        placeholders=[],
        tags=[],
        numbers=[],
        line_breaks=0,
        risk="high",
    )
    issues = check_pair(unit, "这是一段明显超过十二个字的译文", [], length_policy=policy)
    line_issue = next(issue for issue in issues if issue.code == "line_too_long")
    assert line_issue.category == "design"
    assert "策略上限 12" in line_issue.message


def test_qa_uses_display_width_policy() -> None:
    with TemporaryDirectory() as tmp:
        path = Path(tmp) / "length-policy.json"
        path.write_text(
            json.dumps(
                {
                    "default": {
                        "max_line_length": 80,
                        "max_display_width": 10,
                        "max_ratio": 10,
                        "min_ratio": 0.01,
                        "min_source_length": 1,
                    }
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        policy = read_length_policy(path)

    unit = make_unit("전투 시작")
    issues = check_pair(unit, "<color=#fff>战斗开始了呀</color>", [], length_policy=policy)
    display_issue = next(issue for issue in issues if issue.code == "line_display_too_wide")
    assert display_issue.category == "design"
    assert "显示宽度 12" in display_issue.message
    assert display_width("<color=#fff>{0}战斗</color>") == 7
