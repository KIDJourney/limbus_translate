#!/usr/bin/env bash
set -euo pipefail

LOCALIZE_URL=${LOCALIZE_URL:-https://github.com/LocalizeLimbusCompany/LocalizeLimbusCompany.git}
LOCALIZE_REPO=${LOCALIZE_REPO:-build/real-localize}
LOCALIZE_COMMIT=${LOCALIZE_COMMIT:-origin/main}
LOCALIZE_BASE=${LOCALIZE_BASE:-}
WORK_DIR=${WORK_DIR:-build/current-review}
GLOSSARY_PATH=${GLOSSARY_PATH:-$WORK_DIR/paratranz-6860.json}
GLOSSARY_FALLBACK=${GLOSSARY_FALLBACK:-build/current-real/paratranz-6860.json}
OUTPUT_DIR=${OUTPUT_DIR:-$WORK_DIR/LLC_zh-CN-candidates}
SCAN_POLICY=${SCAN_POLICY:-config/scan-policy.sample.json}
LORE_INPUT=${LORE_INPUT:-docs/lore}
TERMS_CACHE=${TERMS_CACHE:-$WORK_DIR/refined-terms-cache.json}
PROVIDER=${PROVIDER:-dry-run}
TERMS_PROVIDER=${TERMS_PROVIDER:-rules}
LIMIT=${LIMIT:-}

echo "Preparing a Localize review pack from KR to GitHub LLC_zh-CN target baseline."
echo "Existing Chinese translations are preserved; only gap units are sent through the workflow."

if [[ ! -d "$LOCALIZE_REPO/.git" ]]; then
  mkdir -p "$(dirname "$LOCALIZE_REPO")"
  git clone "$LOCALIZE_URL" "$LOCALIZE_REPO"
fi

git -C "$LOCALIZE_REPO" fetch origin main
git -C "$LOCALIZE_REPO" checkout --detach "$LOCALIZE_COMMIT"
RESOLVED_COMMIT=$(git -C "$LOCALIZE_REPO" rev-parse HEAD)

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

workflow_args=(
  workflow run
  --source "$LOCALIZE_REPO/KR"
  --target "$LOCALIZE_REPO/LLC_zh-CN"
  --output "$OUTPUT_DIR"
  --work-dir "$WORK_DIR"
  --scan-policy "$SCAN_POLICY"
  --glossary "$GLOSSARY_PATH"
  --lore-input "$LORE_INPUT"
  --terms-cache "$TERMS_CACHE"
  --provider "$PROVIDER"
  --terms-provider "$TERMS_PROVIDER"
)

if [[ -n "$LIMIT" ]]; then
  workflow_args+=(--limit "$LIMIT")
fi

if [[ -n "$LOCALIZE_BASE" ]]; then
  workflow_args+=(
    --localize-repo "$LOCALIZE_REPO"
    --localize-base "$LOCALIZE_BASE"
    --localize-head HEAD
  )
fi

python3 -m limbus_translate.cli "${workflow_args[@]}"

SUMMARY_PATH="$WORK_DIR/summary.json" RESOLVED_COMMIT="$RESOLVED_COMMIT" PROVIDER="$PROVIDER" LIMIT="$LIMIT" python3 - <<'PY'
import json
import os
from pathlib import Path

summary_path = Path(os.environ["SUMMARY_PATH"])
summary = json.loads(summary_path.read_text(encoding="utf-8"))
artifacts = summary.get("artifacts", {})
payload = {
    "localize_commit": os.environ["RESOLVED_COMMIT"],
    "mode": "review-pack",
    "provider": os.environ["PROVIDER"],
    "limit": int(os.environ["LIMIT"]) if os.environ.get("LIMIT") else None,
    "units": summary.get("units"),
    "translated": summary.get("translated"),
    "by_reason": summary.get("by_reason", {}),
    "qa_issues": summary.get("qa_issues"),
    "term_candidates": summary.get("terms", {}).get("candidates", 0),
    "refined_terms": summary.get("terms", {}).get("refined", 0),
    "translation_review_csv": artifacts.get("translation_review_csv"),
    "term_review_csv": artifacts.get("term_review_csv"),
    "summary": str(summary_path),
}
print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
PY

echo "Localize review pack prepared under: $WORK_DIR"
