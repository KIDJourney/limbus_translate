#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

LOCALIZE_COMMIT=${LOCALIZE_COMMIT:-9184302e785805924807919587cd5264186b19eb}
LOCALIZE_REPO=${LOCALIZE_REPO:-build/real-localize}
STATE_PATH=${STATE_PATH:-data/state/localize-reviewed-9184302e.json}
WORK_DIR=${WORK_DIR:-build/current-real}
ARTIFACT_DIR=${ARTIFACT_DIR:-artifacts/localize-${LOCALIZE_COMMIT:0:8}}

export LOCALIZE_COMMIT
export LOCALIZE_REPO
export STATE_PATH
export WORK_DIR

"$SCRIPT_DIR/reproduce-current-localize.sh"

mkdir -p "$ARTIFACT_DIR"
cp "$WORK_DIR/finalize/localize-translation.patch" "$ARTIFACT_DIR/localize-translation.patch"

ARTIFACT_DIR="$ARTIFACT_DIR" \
LOCALIZE_COMMIT="$LOCALIZE_COMMIT" \
STATE_PATH="$STATE_PATH" \
WORK_DIR="$WORK_DIR" \
python3 - <<'PY'
import json
import os
from pathlib import Path

artifact_dir = Path(os.environ["ARTIFACT_DIR"])
localize_commit = os.environ["LOCALIZE_COMMIT"]
work_dir = Path(os.environ["WORK_DIR"])
state_path = Path(os.environ["STATE_PATH"])

units = json.loads((work_dir / "missing-units.json").read_text(encoding="utf-8"))
state_rows = json.loads(state_path.read_text(encoding="utf-8"))
summary = json.loads((work_dir / "finalize" / "summary.json").read_text(encoding="utf-8"))

state_by_key = {}
for row in state_rows:
    for key in (row.get("unit_id"), row.get("source_hash"), row.get("stable_key")):
        if key:
            state_by_key[key] = row

translations = []
for unit in units:
    state = None
    for key in (unit.get("unit_id"), unit.get("source_hash"), unit.get("stable_key")):
        if key in state_by_key:
            state = state_by_key[key]
            break
    if not state or not state.get("target_text"):
        raise SystemExit(f"missing reviewed target for unit {unit.get('unit_id')}")
    translations.append(
        {
            "relative_file": unit["relative_file"],
            "json_path": unit["json_path"],
            "source_json_path": unit.get("source_json_path") or unit["json_path"],
            "stable_key": unit.get("stable_key"),
            "reason": unit["reason"],
            "source_text": unit["source_text"],
            "previous_target_text": unit.get("target_text"),
            "target_text": state["target_text"],
            "status": state["status"],
        }
    )

reason_counts = {}
for unit in units:
    reason_counts[unit["reason"]] = reason_counts.get(unit["reason"], 0) + 1

portable_summary = {
    "localize_commit": localize_commit,
    "source_dir": "KR",
    "target_baseline_dir": "LLC_zh-CN",
    "mode": "gap-only",
    "unit_count": len(units),
    "reason_counts": dict(sorted(reason_counts.items())),
    "reviewed_units": summary["state"]["ready_units"],
    "patch": "localize-translation.patch",
    "patch_replacements": summary["localize_patch"]["replacements"],
    "patch_changed_files": summary["localize_patch"]["changed_files"],
    "patch_apply_check": summary["localize_patch"]["apply_check"],
    "qa_issues": summary["qa_issues"],
    "visible_hangul_warnings": summary["visible_hangul"]["warnings"],
}

readme = f"""# LocalizeLimbusCompany {localize_commit[:8]} Gap Patch

This artifact is generated from LocalizeLimbusCompany commit `{localize_commit}`.

- Source baseline: `KR`
- Target baseline: GitHub `LLC_zh-CN`
- Mode: gap-only; existing Chinese translations are preserved
- Units: {len(units)} `{next(iter(portable_summary["reason_counts"]), "unknown")}` gaps
- Patch: `localize-translation.patch`
- Translation table: `translations.json`
- Verification summary: `summary.json`

Apply inside a LocalizeLimbusCompany checkout at the same commit:

```bash
git apply /path/to/limbus_translate/{artifact_dir.as_posix()}/localize-translation.patch
```
"""

artifact_dir.joinpath("summary.json").write_text(
    json.dumps(portable_summary, ensure_ascii=False, indent=2) + "\n",
    encoding="utf-8",
)
artifact_dir.joinpath("translations.json").write_text(
    json.dumps({"translations": translations}, ensure_ascii=False, indent=2) + "\n",
    encoding="utf-8",
)
artifact_dir.joinpath("README.md").write_text(readme, encoding="utf-8")

print(
    json.dumps(
        {
            "artifact": artifact_dir.as_posix(),
            "translations": len(translations),
            "patch_replacements": portable_summary["patch_replacements"],
            "qa_issues": portable_summary["qa_issues"],
            "visible_hangul_warnings": portable_summary["visible_hangul_warnings"],
        },
        ensure_ascii=False,
        sort_keys=True,
    )
)
PY

git -C "$LOCALIZE_REPO" apply --check "$REPO_ROOT/$ARTIFACT_DIR/localize-translation.patch"

echo "published gap-only Localize artifact: $ARTIFACT_DIR"
