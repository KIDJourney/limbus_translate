#!/usr/bin/env bash
set -euo pipefail

LOCALIZE_URL=${LOCALIZE_URL:-https://github.com/LocalizeLimbusCompany/LocalizeLimbusCompany.git}
LOCALIZE_REPO=${LOCALIZE_REPO:-build/real-localize}
LOCALIZE_COMMIT=${LOCALIZE_COMMIT:-9184302e785805924807919587cd5264186b19eb}
STATE_PATH=${STATE_PATH:-data/state/localize-reviewed-9184302e.json}
WORK_DIR=${WORK_DIR:-build/current-real}
GLOSSARY_PATH=${GLOSSARY_PATH:-$WORK_DIR/paratranz-6860.json}
PATCH_PATH=${PATCH_PATH:-$WORK_DIR/finalize/localize-translation.patch}
SUMMARY_PATH="$WORK_DIR/finalize/summary.json"

echo "Using GitHub LLC_zh-CN as the target baseline; only untranslated or still-Korean gaps will be scanned."

if [[ ! -d "$LOCALIZE_REPO/.git" ]]; then
  mkdir -p "$(dirname "$LOCALIZE_REPO")"
  git clone "$LOCALIZE_URL" "$LOCALIZE_REPO"
fi

git -C "$LOCALIZE_REPO" fetch origin main
git -C "$LOCALIZE_REPO" checkout --detach "$LOCALIZE_COMMIT"

python3 -m limbus_translate.cli glossary sync-paratranz \
  --project-id 6860 \
  --output "$GLOSSARY_PATH"

python3 -m limbus_translate.cli scan \
  --source "$LOCALIZE_REPO/KR" \
  --target "$LOCALIZE_REPO/LLC_zh-CN" \
  --output "$WORK_DIR/missing-units.json" \
  --scan-policy config/scan-policy.sample.json

python3 -m limbus_translate.cli workflow finalize \
  --source "$LOCALIZE_REPO/KR" \
  --target "$LOCALIZE_REPO/LLC_zh-CN" \
  --units "$WORK_DIR/missing-units.json" \
  --state "$STATE_PATH" \
  --output "$WORK_DIR/finalize/LLC_zh-CN-reviewed" \
  --work-dir "$WORK_DIR/finalize" \
  --glossary "$GLOSSARY_PATH" \
  --localize-repo "$LOCALIZE_REPO" \
  --patch-output "$PATCH_PATH" \
  --fail-if-pending \
  --fail-on-error

SUMMARY_PATH="$SUMMARY_PATH" python3 - <<'PY'
import json
import os
from pathlib import Path

summary = json.loads(Path(os.environ["SUMMARY_PATH"]).read_text(encoding="utf-8"))
assert summary["units"] == 22, summary
assert summary["applied"] == 22, summary
assert summary["localize_patch"]["replacements"] == 22, summary
assert summary["localize_patch"]["apply_check"] is True, summary
assert summary["qa_issues"] == 0, summary
assert summary["visible_hangul"]["warnings"] == 0, summary
print("incremental gap-only reproduction verified: 22 units, 22 replacements")
PY

echo "current Localize patch reproduced: $PATCH_PATH"
