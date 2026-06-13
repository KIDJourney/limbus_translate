from pathlib import Path
import json
import tempfile

from limbus_translate.providers import DryRunProvider
from limbus_translate.scanner import scan_missing
from limbus_translate.state import UnitState, read_state, summarize_state_coverage, write_state
from limbus_translate.translator import apply_state_translations, overlay_existing_target, translate_units


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


def test_state_apply_writes_reviewed_translation_without_provider() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        source = root / "KR"
        target = root / "LLC_zh-CN"
        output = root / "reviewed"
        source.mkdir()
        target.mkdir()
        (source / "Sample.json").write_text(
            json.dumps({"dataList": [{"id": 1, "desc": "새 문장입니다."}]}, ensure_ascii=False),
            encoding="utf-8",
        )
        (target / "Sample.json").write_text(
            json.dumps({"dataList": [{"id": 1, "desc": ""}]}, ensure_ascii=False),
            encoding="utf-8",
        )
        units = scan_missing(source, target)
        state_path = root / "state.json"
        write_state(
            state_path,
            [
                UnitState(
                    unit_id=units[0].unit_id,
                    source_hash=None,
                    stable_key=None,
                    status="reviewed",
                    target_text="新的句子。",
                )
            ],
        )
        overlay_existing_target(source, target, output)
        count = apply_state_translations(
            source_root=source,
            target_root=target,
            output_root=output,
            units=units,
            states=read_state(state_path),
        )
        data = json.loads((output / "Sample.json").read_text(encoding="utf-8"))

    assert count == 1
    assert data["dataList"][0]["desc"] == "新的句子。"


def test_state_status_reports_ready_and_pending_units() -> None:
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
                        {"id": 1, "desc": "첫 문장입니다."},
                        {"id": 2, "desc": "두 번째 문장입니다."},
                    ]
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        (target / "Sample.json").write_text(
            json.dumps({"dataList": [{"id": 1, "desc": ""}, {"id": 2, "desc": ""}]}, ensure_ascii=False),
            encoding="utf-8",
        )
        units = scan_missing(source, target)
        states = {
            units[0].unit_id: UnitState(
                unit_id=units[0].unit_id,
                source_hash=None,
                stable_key=None,
                status="reviewed",
                target_text="第一句。",
            ),
            units[1].unit_id: UnitState(
                unit_id=units[1].unit_id,
                source_hash=None,
                stable_key=None,
                status="new",
                target_text=None,
            ),
        }

    summary = summarize_state_coverage(units, states)

    assert summary["total_units"] == 2
    assert summary["ready_units"] == 1
    assert summary["pending_units"] == 1
    assert summary["with_target_text"] == 1
    assert summary["missing_target_text"] == 1
    assert summary["by_status"] == {"new": 1, "reviewed": 1}
    assert not summary["ready"]
