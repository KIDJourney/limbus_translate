#!/usr/bin/env bash
set -euo pipefail

LOCALIZE_URL=${LOCALIZE_URL:-https://github.com/LocalizeLimbusCompany/LocalizeLimbusCompany.git}
LOCALIZE_REPO=${LOCALIZE_REPO:-build/real-localize}
WORK_DIR=${WORK_DIR:-build/current-review}
SCAN_POLICY=${SCAN_POLICY:-config/scan-policy.sample.json}
GLOSSARY_PATH=${GLOSSARY_PATH:-$WORK_DIR/paratranz-6860.json}
GLOSSARY_FALLBACK=${GLOSSARY_FALLBACK:-build/current-real/paratranz-6860.json}
REVIEW_CSV=${REVIEW_CSV:-$WORK_DIR/translation-review/review.csv}
STATE_PATH=${STATE_PATH:-}
GENERATED_STATE_PATH=${GENERATED_STATE_PATH:-$WORK_DIR/reviewed-state.json}
UNITS_PATH=${UNITS_PATH:-$WORK_DIR/missing-units.json}
FINALIZE_WORK_DIR=${FINALIZE_WORK_DIR:-$WORK_DIR/finalize}
OUTPUT_DIR=${OUTPUT_DIR:-$FINALIZE_WORK_DIR/LLC_zh-CN-reviewed}
PATCH_PATH=${PATCH_PATH:-$FINALIZE_WORK_DIR/localize-translation.patch}
LOCALIZE_COMMIT=${LOCALIZE_COMMIT:-}
METADATA_PATH=${METADATA_PATH:-$WORK_DIR/localize-review-metadata.json}

echo "Finalizing a reviewed Localize translation pack against the GitHub LLC_zh-CN target baseline."
echo "No translation provider is called; only approved review rows or an existing reviewed state are applied."

if [[ ! -d "$LOCALIZE_REPO/.git" ]]; then
  mkdir -p "$(dirname "$LOCALIZE_REPO")"
  git clone "$LOCALIZE_URL" "$LOCALIZE_REPO"
fi

if [[ -z "$LOCALIZE_COMMIT" && -f "$METADATA_PATH" ]]; then
  LOCALIZE_COMMIT=$(METADATA_PATH="$METADATA_PATH" python3 - <<'PY'
import json
import os
from pathlib import Path

metadata = json.loads(Path(os.environ["METADATA_PATH"]).read_text(encoding="utf-8"))
print(metadata.get("localize_commit", ""))
PY
)
fi
LOCALIZE_COMMIT=${LOCALIZE_COMMIT:-origin/main}

git -C "$LOCALIZE_REPO" fetch origin main
git -C "$LOCALIZE_REPO" checkout --detach "$LOCALIZE_COMMIT"
RESOLVED_COMMIT=$(git -C "$LOCALIZE_REPO" rev-parse HEAD)

if [[ ! -f "$GLOSSARY_PATH" ]]; then
  if ! python3 -m limbus_translate.cli glossary sync-paratranz \
    --project-id 6860 \
    --output "$GLOSSARY_PATH"; then
    if [[ -f "$GLOSSARY_FALLBACK" ]]; then
      mkdir -p "$(dirname "$GLOSSARY_PATH")"
      cp "$GLOSSARY_FALLBACK" "$GLOSSARY_PATH"
      echo "Paratranz sync failed; reused cached glossary: $GLOSSARY_FALLBACK"
    else
      echo "Paratranz sync failed and no fallback glossary exists: $GLOSSARY_FALLBACK" >&2
      exit 1
    fi
  fi
fi

if [[ -z "$STATE_PATH" ]]; then
  if [[ ! -f "$REVIEW_CSV" ]]; then
    echo "review CSV does not exist: $REVIEW_CSV" >&2
    exit 1
  fi
  python3 -m limbus_translate.cli review apply \
    --review "$REVIEW_CSV" \
    --output "$GENERATED_STATE_PATH"
  STATE_PATH="$GENERATED_STATE_PATH"
fi

python3 -m limbus_translate.cli scan \
  --source "$LOCALIZE_REPO/KR" \
  --target "$LOCALIZE_REPO/LLC_zh-CN" \
  --output "$UNITS_PATH" \
  --scan-policy "$SCAN_POLICY"

python3 -m limbus_translate.cli workflow finalize \
  --source "$LOCALIZE_REPO/KR" \
  --target "$LOCALIZE_REPO/LLC_zh-CN" \
  --units "$UNITS_PATH" \
  --state "$STATE_PATH" \
  --output "$OUTPUT_DIR" \
  --work-dir "$FINALIZE_WORK_DIR" \
  --glossary "$GLOSSARY_PATH" \
  --localize-repo "$LOCALIZE_REPO" \
  --patch-output "$PATCH_PATH" \
  --fail-if-pending \
  --fail-on-error

git -C "$LOCALIZE_REPO" apply --check "$(pwd)/$PATCH_PATH"

SUMMARY_PATH="$FINALIZE_WORK_DIR/summary.json" \
RESOLVED_COMMIT="$RESOLVED_COMMIT" \
STATE_PATH="$STATE_PATH" \
PATCH_PATH="$PATCH_PATH" \
python3 - <<'PY'
import json
import os
from pathlib import Path

summary = json.loads(Path(os.environ["SUMMARY_PATH"]).read_text(encoding="utf-8"))
payload = {
    "localize_commit": os.environ["RESOLVED_COMMIT"],
    "state": os.environ["STATE_PATH"],
    "units": summary.get("units"),
    "applied": summary.get("applied"),
    "pending_units": summary.get("state", {}).get("pending_units"),
    "qa_issues": summary.get("qa_issues"),
    "visible_hangul_warnings": summary.get("visible_hangul", {}).get("warnings"),
    "patch": os.environ["PATCH_PATH"],
    "patch_replacements": summary.get("localize_patch", {}).get("replacements"),
    "patch_apply_check": summary.get("localize_patch", {}).get("apply_check"),
}
print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
PY

echo "Reviewed Localize translation pack finalized: $PATCH_PATH"
