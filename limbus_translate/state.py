from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .scanner import TranslationUnit


LOCKED_STATUSES = {"reviewed", "locked"}


@dataclass(frozen=True)
class UnitState:
    unit_id: str | None
    source_hash: str | None
    stable_key: str | None
    status: str
    target_text: str | None = None
    note: str = ""


def read_state(path: Path) -> dict[str, UnitState]:
    if not path.exists():
        return {}
    rows = json.loads(path.read_text(encoding="utf-8"))
    states = [UnitState(**row) for row in rows]
    indexed: dict[str, UnitState] = {}
    for state in states:
        for key in [state.unit_id, state.source_hash, state.stable_key]:
            if key:
                indexed[key] = state
    return indexed


def write_state(path: Path, states: list[UnitState]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump([asdict(state) for state in states], handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def state_for_unit(unit: TranslationUnit, states: dict[str, UnitState]) -> UnitState | None:
    for key in [unit.unit_id, unit.source_hash, unit.stable_key]:
        if key and key in states:
            return states[key]
    return None


def is_locked(unit: TranslationUnit, states: dict[str, UnitState]) -> bool:
    state = state_for_unit(unit, states)
    return state is not None and state.status in LOCKED_STATUSES


def summarize_state_coverage(units: list[TranslationUnit], states: dict[str, UnitState]) -> dict[str, Any]:
    by_status: dict[str, int] = {}
    ready_units = 0
    with_target_text = 0
    missing_state = 0
    missing_target_text = 0
    for unit in units:
        state = state_for_unit(unit, states)
        if state is None:
            missing_state += 1
            by_status["missing_state"] = by_status.get("missing_state", 0) + 1
            continue
        by_status[state.status] = by_status.get(state.status, 0) + 1
        if state.target_text:
            with_target_text += 1
        else:
            missing_target_text += 1
        if state.status in LOCKED_STATUSES and state.target_text:
            ready_units += 1
    total_units = len(units)
    pending_units = total_units - ready_units
    return {
        "total_units": total_units,
        "ready_units": ready_units,
        "pending_units": pending_units,
        "with_target_text": with_target_text,
        "missing_state": missing_state,
        "missing_target_text": missing_target_text,
        "by_status": dict(sorted(by_status.items())),
        "ready": pending_units == 0,
    }
