import csv
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from limbus_translate.providers import DryRunProvider
from limbus_translate.qa import qa_output
from limbus_translate.review import apply_translation_review_csv, write_translation_review_pack
from limbus_translate.scanner import scan_missing
from limbus_translate.translator import overlay_existing_target, translate_units


def test_translation_review_pack_exports_qa_and_apply_review_state() -> None:
    with TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        source = root / "KR"
        target = root / "LLC_zh-CN"
        output = root / "out"
        review_dir = root / "translation-review"
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
        overlay_existing_target(source, target, output)
        translate_units(
            source_root=source,
            target_root=target,
            output_root=output,
            units=units,
            glossary=[],
            provider=DryRunProvider(),
        )
        issues = qa_output(units=units, output_root=output, glossary=[])
        summary = write_translation_review_pack(review_dir, units=units, output_root=output, issues=issues)
        with (review_dir / "review.csv").open("r", encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.DictReader(handle))
        jsonl_rows = [json.loads(line) for line in (review_dir / "review.jsonl").read_text(encoding="utf-8").splitlines()]

        rows[0]["approved"] = "yes"
        rows[0]["revised_target"] = "新的句子。"
        rows[0]["reviewer_note"] = "tone checked"
        with (review_dir / "approved.csv").open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
        states = apply_translation_review_csv(review_dir / "approved.csv")

    assert summary["selected"] == 1
    assert rows[0]["source_text"] == "새 문장입니다."
    assert rows[0]["proposed_text"] == "[待译] 새 문장입니다."
    assert rows[0]["qa_severity"] == "warning"
    assert rows[0]["qa_codes"] == "hangul_residue"
    assert jsonl_rows[0]["unit_id"] == units[0].unit_id
    assert len(states) == 1
    assert states[0].unit_id == units[0].unit_id
    assert states[0].status == "reviewed"
    assert states[0].target_text == "新的句子。"
    assert "tone checked" in states[0].note
