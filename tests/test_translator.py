from pathlib import Path
import json
import tempfile

from limbus_translate.providers import DryRunProvider
from limbus_translate.scanner import scan_missing
from limbus_translate.translator import overlay_existing_target, translate_units


def test_translate_appends_missing_data_list_record() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        source = root / "KR"
        target = root / "LLC_zh-CN"
        output = root / "out"
        source.mkdir()
        target.mkdir()
        (source / "Sample.json").write_text(
            json.dumps(
                {
                    "dataList": [
                        {"id": 1, "desc": "이미 있음."},
                        {"id": 2, "desc": "새 기록입니다.", "name": "새 기록"},
                    ]
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        (target / "Sample.json").write_text(
            json.dumps({"dataList": [{"id": 1, "desc": "已有。"}]}, ensure_ascii=False),
            encoding="utf-8",
        )
        units = scan_missing(source, target)
        overlay_existing_target(source, target, output)
        count = translate_units(
            source_root=source,
            target_root=target,
            output_root=output,
            units=units,
            glossary=[],
            provider=DryRunProvider(),
        )
        data = json.loads((output / "Sample.json").read_text(encoding="utf-8"))
    assert count == 2
    assert [row["id"] for row in data["dataList"]] == [1, 2]
    appended = data["dataList"][1]
    assert appended["desc"].startswith("[待译]")
