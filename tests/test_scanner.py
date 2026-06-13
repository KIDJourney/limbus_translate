from pathlib import Path

from limbus_translate.scanner import scan_missing


def test_scan_missing_detects_korean_target_and_blank_target() -> None:
    root = Path("tests/fixtures/localize")
    units = scan_missing(root / "KR", root / "LLC_zh-CN")
    paths = {unit.json_path: unit.reason for unit in units}
    assert paths["dataList.0.desc"] == "target_same_as_source"
    assert paths["dataList.0.options.0.result.0"] == "missing_target_text"
    assert "dataList.0.name" not in paths
    assert "dataList.0.options.0.message" not in paths
    assert "dataList.1.name" not in paths
