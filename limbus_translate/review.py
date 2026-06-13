from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from .json_paths import get_path
from .qa import QaIssue
from .scanner import TranslationUnit, load_json
from .state import UnitState
from .terms import is_approved


REVIEW_FIELDNAMES = [
    "unit_id",
    "relative_file",
    "json_path",
    "source_text",
    "previous_target",
    "proposed_text",
    "approved",
    "revised_target",
    "reviewer_note",
    "qa_severity",
    "qa_codes",
    "qa_messages",
    "reason",
    "risk",
    "source_hash",
    "stable_key",
]


def write_translation_review_pack(
    output_dir: Path,
    *,
    units: list[TranslationUnit],
    output_root: Path,
    issues: list[QaIssue],
) -> dict[str, int | str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    review_csv = output_dir / "review.csv"
    review_jsonl = output_dir / "review.jsonl"
    grouped_issues = issues_by_location(issues)
    loaded: dict[str, Any] = {}

    rows: list[dict[str, str]] = []
    for unit in units:
        proposed_text = translated_text_for_unit(unit, output_root, loaded)
        unit_issues = grouped_issues.get(location_key(unit.relative_file, unit.json_path), [])
        rows.append(review_row(unit, proposed_text, unit_issues))

    with review_csv.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=REVIEW_FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)

    with review_jsonl.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True))
            handle.write("\n")

    return {"selected": len(rows), "review_csv": str(review_csv), "review_jsonl": str(review_jsonl)}


def apply_translation_review_csv(path: Path, *, status: str = "reviewed") -> list[UnitState]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    states: list[UnitState] = []
    for row in rows:
        if not is_approved(str(row.get("approved", ""))):
            continue
        target = str(row.get("revised_target", "")).strip() or str(row.get("proposed_text", "")).strip()
        if not target:
            continue
        note_parts = [
            str(row.get("reviewer_note", "")).strip(),
            f"qa_codes={str(row.get('qa_codes', '')).strip()}",
            f"review_status={status}",
        ]
        states.append(
            UnitState(
                unit_id=empty_to_none(row.get("unit_id")),
                source_hash=empty_to_none(row.get("source_hash")),
                stable_key=empty_to_none(row.get("stable_key")),
                status=status,
                target_text=target,
                note="; ".join(part for part in note_parts if part and not part.endswith("=")),
            )
        )
    return states


def read_qa_issues(path: Path) -> list[QaIssue]:
    if not path.exists():
        return []
    rows = json.loads(path.read_text(encoding="utf-8"))
    return [QaIssue(**row) for row in rows]


def merge_state_rows(existing: list[UnitState], updates: list[UnitState]) -> list[UnitState]:
    merged: dict[str, UnitState] = {}
    order: list[str] = []
    for state in [*existing, *updates]:
        key = state_merge_key(state)
        if not key:
            continue
        if key not in merged:
            order.append(key)
        merged[key] = state
    return [merged[key] for key in order]


def read_state_rows(path: Path) -> list[UnitState]:
    if not path.exists():
        return []
    rows = json.loads(path.read_text(encoding="utf-8"))
    return [UnitState(**row) for row in rows]


def state_merge_key(state: UnitState) -> str:
    for key in [state.unit_id, state.source_hash, state.stable_key]:
        if key:
            return key
    return ""


def review_row(unit: TranslationUnit, proposed_text: str, issues: list[QaIssue]) -> dict[str, str]:
    return {
        "unit_id": unit.unit_id,
        "relative_file": unit.relative_file,
        "json_path": unit.json_path,
        "source_text": unit.source_text,
        "previous_target": unit.target_text or "",
        "proposed_text": proposed_text,
        "approved": "",
        "revised_target": "",
        "reviewer_note": "",
        "qa_severity": highest_severity(issues),
        "qa_codes": " | ".join(issue.code for issue in issues),
        "qa_messages": " | ".join(issue.message for issue in issues),
        "reason": unit.reason,
        "risk": unit.risk,
        "source_hash": unit.source_hash,
        "stable_key": unit.stable_key or "",
    }


def translated_text_for_unit(unit: TranslationUnit, output_root: Path, loaded: dict[str, Any]) -> str:
    if unit.relative_file not in loaded:
        output_file = output_root / unit.relative_file
        loaded[unit.relative_file] = load_json(output_file) if output_file.exists() else None
    data = loaded[unit.relative_file]
    if data is None:
        return ""
    try:
        value = get_path(data, tuple(unit.json_path.split(".")))
    except (KeyError, IndexError, ValueError):
        return ""
    return value if isinstance(value, str) else ""


def issues_by_location(issues: list[QaIssue]) -> dict[str, list[QaIssue]]:
    grouped: dict[str, list[QaIssue]] = {}
    for issue in issues:
        grouped.setdefault(location_key(issue.relative_file, issue.json_path), []).append(issue)
    return grouped


def location_key(relative_file: str, json_path: str) -> str:
    return f"{relative_file}\0{json_path}"


def highest_severity(issues: list[QaIssue]) -> str:
    order = {"error": 2, "warning": 1}
    highest = ""
    for issue in issues:
        if order.get(issue.severity, 0) > order.get(highest, 0):
            highest = issue.severity
    return highest


def empty_to_none(value: object) -> str | None:
    text = "" if value is None else str(value).strip()
    return text or None
