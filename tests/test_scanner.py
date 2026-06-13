from pathlib import Path
import json
import tempfile

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


def test_scan_aligns_data_list_by_id_when_order_changes() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        source = root / "KR"
        target = root / "LLC_zh-CN"
        source.mkdir()
        target.mkdir()
        (source / "Sample.json").write_text(
            json.dumps(
                {
                    "dataList": [
                        {"id": 1, "desc": "새로운 문장입니다."},
                        {"id": 2, "desc": "이미 번역됨."},
                    ]
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        (target / "Sample.json").write_text(
            json.dumps(
                {
                    "dataList": [
                        {"id": 2, "desc": "已经翻译。"},
                        {"id": 1, "desc": "새로운 문장입니다."},
                    ]
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        units = scan_missing(source, target)
    assert len(units) == 1
    assert units[0].source_json_path == "dataList.0.desc"
    assert units[0].json_path == "dataList.1.desc"
    assert units[0].stable_key == "dataList[id=1].desc"


def test_scan_reports_missing_data_list_record() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        source = root / "KR"
        target = root / "LLC_zh-CN"
        source.mkdir()
        target.mkdir()
        (source / "Sample.json").write_text(
            json.dumps({"dataList": [{"id": 9, "desc": "새 기록입니다."}]}, ensure_ascii=False),
            encoding="utf-8",
        )
        (target / "Sample.json").write_text(
            json.dumps({"dataList": []}, ensure_ascii=False),
            encoding="utf-8",
        )
        units = scan_missing(source, target)
    assert len(units) == 1
    assert units[0].reason == "missing_target_record"
    assert units[0].stable_key == "dataList[id=9].desc"
