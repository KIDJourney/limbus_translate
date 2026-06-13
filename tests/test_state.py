from pathlib import Path
import json
import tempfile

from limbus_translate.providers import DryRunProvider
from limbus_translate.scanner import scan_missing
from limbus_translate.state import UnitState, write_state, read_state
from limbus_translate.translator import overlay_existing_target, translate_units


def test_translate_skips_locked_unit() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        source = root / "KR"
        target = root / "LLC_zh-CN"
        output = root / "out"
        source.mkdir()
        target.mkdir()
        (source / "Sample.json").write_text(
            json.dumps({"dataList": [{"id": 1, "desc": "새 문장입니다."}]}, ensure_ascii=False),
            encoding="utf-8",
        )
        (target / "Sample.json").write_text(
            json.dumps({"dataList": [{"id": 1, "desc": "새 문장입니다."}]}, ensure_ascii=False),
            encoding="utf-8",
        )
        units = scan_missing(source, target)
        state_path = root / "state.json"
        write_state(
            state_path,
            [UnitState(unit_id=units[0].unit_id, source_hash=None, stable_key=None, status="locked")],
        )
        overlay_existing_target(source, target, output)
        count = translate_units(
            source_root=source,
            target_root=target,
            output_root=output,
            units=units,
            glossary=[],
            provider=DryRunProvider(),
            states=read_state(state_path),
        )
        data = json.loads((output / "Sample.json").read_text(encoding="utf-8"))
    assert count == 0
    assert data["dataList"][0]["desc"] == "새 문장입니다."
