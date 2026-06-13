from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

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
