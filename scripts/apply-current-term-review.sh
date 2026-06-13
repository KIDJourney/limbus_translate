#!/usr/bin/env bash
set -euo pipefail

WORK_DIR=${WORK_DIR:-build/current-review}
REVIEW_CSV=${REVIEW_CSV:-$WORK_DIR/term-review/review.csv}
PARATRANZ_PATH=${PARATRANZ_PATH:-$WORK_DIR/paratranz-6860.json}
PARATRANZ_FALLBACK=${PARATRANZ_FALLBACK:-build/current-real/paratranz-6860.json}
LOCAL_REVIEWED_PATH=${LOCAL_REVIEWED_PATH:-cache/glossary/local-reviewed.json}
ACTIVE_GLOSSARY_PATH=${ACTIVE_GLOSSARY_PATH:-cache/glossary/active.json}
NEW_REVIEWED_PATH=${NEW_REVIEWED_PATH:-$WORK_DIR/local-reviewed-new.json}
MERGED_LOCAL_PATH=${MERGED_LOCAL_PATH:-$WORK_DIR/local-reviewed-merged.json}
AUDIT_REPORT=${AUDIT_REPORT:-$WORK_DIR/active-glossary-audit.json}

echo "Applying approved term review rows into the local reviewed glossary cache."

if [[ ! -f "$REVIEW_CSV" ]]; then
  echo "term review CSV does not exist: $REVIEW_CSV" >&2
  exit 1
fi

python3 -m limbus_translate.cli terms apply-review \
  --review "$REVIEW_CSV" \
  --output "$NEW_REVIEWED_PATH"

if [[ -f "$LOCAL_REVIEWED_PATH" ]]; then
  python3 -m limbus_translate.cli glossary merge \
    --input "$LOCAL_REVIEWED_PATH" \
    --input "$NEW_REVIEWED_PATH" \
    --output "$MERGED_LOCAL_PATH"
else
  mkdir -p "$(dirname "$MERGED_LOCAL_PATH")"
  cp "$NEW_REVIEWED_PATH" "$MERGED_LOCAL_PATH"
fi

mkdir -p "$(dirname "$LOCAL_REVIEWED_PATH")"
cp "$MERGED_LOCAL_PATH" "$LOCAL_REVIEWED_PATH"

if [[ ! -f "$PARATRANZ_PATH" ]]; then
  if ! python3 -m limbus_translate.cli glossary sync-paratranz \
    --project-id 6860 \
    --output "$PARATRANZ_PATH"; then
    if [[ -f "$PARATRANZ_FALLBACK" ]]; then
      mkdir -p "$(dirname "$PARATRANZ_PATH")"
      cp "$PARATRANZ_FALLBACK" "$PARATRANZ_PATH"
      echo "Paratranz sync failed; reused cached glossary: $PARATRANZ_FALLBACK"
    else
      echo "Paratranz sync failed and no fallback glossary exists: $PARATRANZ_FALLBACK" >&2
      exit 1
    fi
  fi
fi

python3 -m limbus_translate.cli glossary merge \
  --input "$PARATRANZ_PATH" \
  --input "$LOCAL_REVIEWED_PATH" \
  --output "$ACTIVE_GLOSSARY_PATH"

python3 -m limbus_translate.cli glossary audit \
  --input "$ACTIVE_GLOSSARY_PATH" \
  --report "$AUDIT_REPORT"

NEW_REVIEWED_PATH="$NEW_REVIEWED_PATH" \
LOCAL_REVIEWED_PATH="$LOCAL_REVIEWED_PATH" \
ACTIVE_GLOSSARY_PATH="$ACTIVE_GLOSSARY_PATH" \
AUDIT_REPORT="$AUDIT_REPORT" \
python3 - <<'PY'
import json
import os
from pathlib import Path

new_terms = json.loads(Path(os.environ["NEW_REVIEWED_PATH"]).read_text(encoding="utf-8"))
local_terms = json.loads(Path(os.environ["LOCAL_REVIEWED_PATH"]).read_text(encoding="utf-8"))
active_terms = json.loads(Path(os.environ["ACTIVE_GLOSSARY_PATH"]).read_text(encoding="utf-8"))
audit = json.loads(Path(os.environ["AUDIT_REPORT"]).read_text(encoding="utf-8"))
payload = {
    "new_reviewed_terms": len(new_terms),
    "local_reviewed_terms": len(local_terms),
    "active_glossary_terms": len(active_terms),
    "active_glossary": os.environ["ACTIVE_GLOSSARY_PATH"],
    "local_reviewed": os.environ["LOCAL_REVIEWED_PATH"],
    "audit_report": os.environ["AUDIT_REPORT"],
    "audit_issues": len(audit.get("issues", [])),
}
print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
PY

echo "Current term review applied into active glossary: $ACTIVE_GLOSSARY_PATH"
