#!/usr/bin/env bash
set -euo pipefail

LOCALIZE_URL=${LOCALIZE_URL:-https://github.com/LocalizeLimbusCompany/LocalizeLimbusCompany.git}
LOCALIZE_REPO=${LOCALIZE_REPO:-build/real-localize}
LOCALIZE_COMMIT=${LOCALIZE_COMMIT:-origin/main}
WORK_DIR=${WORK_DIR:-build/current-model-eval}
GLOSSARY_PATH=${GLOSSARY_PATH:-$WORK_DIR/paratranz-6860.json}
GLOSSARY_FALLBACK=${GLOSSARY_FALLBACK:-build/current-real/paratranz-6860.json}
GOLD_LIMIT=${GOLD_LIMIT:-1000}
GOLD_PER_GROUP=${GOLD_PER_GROUP:-20}
GOLD_GROUP_BY=${GOLD_GROUP_BY:-tag}
GOLD_SEED=${GOLD_SEED:-7}

echo "Preparing a provider-eval gold review pack from GitHub LLC_zh-CN reference translations."
echo "This does not call a translation provider; it only exports reference rows for human review."

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

python3 -m limbus_translate.cli eval build-gold \
  --source "$LOCALIZE_REPO/KR" \
  --target "$LOCALIZE_REPO/LLC_zh-CN" \
  --glossary "$GLOSSARY_PATH" \
  --output "$WORK_DIR/gold-set.json" \
  --limit "$GOLD_LIMIT"

python3 -m limbus_translate.cli eval sample-gold \
  --gold "$WORK_DIR/gold-set.json" \
  --output "$WORK_DIR/gold-sample.json" \
  --per-group "$GOLD_PER_GROUP" \
  --group-by "$GOLD_GROUP_BY" \
  --seed "$GOLD_SEED"

python3 -m limbus_translate.cli eval review-pack \
  --gold "$WORK_DIR/gold-sample.json" \
  --output-dir "$WORK_DIR/gold-review"

WORK_DIR="$WORK_DIR" \
RESOLVED_COMMIT="$RESOLVED_COMMIT" \
GOLD_LIMIT="$GOLD_LIMIT" \
GOLD_PER_GROUP="$GOLD_PER_GROUP" \
GOLD_GROUP_BY="$GOLD_GROUP_BY" \
GOLD_SEED="$GOLD_SEED" \
python3 - <<'PY'
import csv
import json
import os
from pathlib import Path

work_dir = Path(os.environ["WORK_DIR"])
gold = json.loads((work_dir / "gold-set.json").read_text(encoding="utf-8"))
sample = json.loads((work_dir / "gold-sample.json").read_text(encoding="utf-8"))
with (work_dir / "gold-review" / "review.csv").open("r", encoding="utf-8-sig", newline="") as handle:
    review_rows = list(csv.DictReader(handle))
payload = {
    "localize_commit": os.environ["RESOLVED_COMMIT"],
    "gold_cases": len(gold.get("cases", [])),
    "sample_cases": len(sample.get("cases", [])),
    "review_rows": len(review_rows),
    "gold_limit": int(os.environ["GOLD_LIMIT"]),
    "gold_per_group": int(os.environ["GOLD_PER_GROUP"]),
    "gold_group_by": os.environ["GOLD_GROUP_BY"],
    "gold_seed": int(os.environ["GOLD_SEED"]),
    "review_csv": str(work_dir / "gold-review" / "review.csv"),
    "curated_output_after_review": str(work_dir / "gold-curated.json"),
}
print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
PY

echo "Model eval gold review pack prepared under: $WORK_DIR"
