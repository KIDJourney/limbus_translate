#!/usr/bin/env bash
set -euo pipefail

WORK_DIR=${WORK_DIR:-build/current-model-eval}
GOLD_SAMPLE=${GOLD_SAMPLE:-$WORK_DIR/gold-sample.json}
REVIEW_CSV=${REVIEW_CSV:-$WORK_DIR/gold-review/review.csv}
CURATED_GOLD=${CURATED_GOLD:-$WORK_DIR/gold-curated.json}

echo "Applying approved gold review rows into a curated provider-eval gold set."

if [[ ! -f "$GOLD_SAMPLE" ]]; then
  echo "gold sample does not exist: $GOLD_SAMPLE" >&2
  exit 1
fi

if [[ ! -f "$REVIEW_CSV" ]]; then
  echo "gold review CSV does not exist: $REVIEW_CSV" >&2
  exit 1
fi

python3 -m limbus_translate.cli eval apply-review \
  --gold "$GOLD_SAMPLE" \
  --review "$REVIEW_CSV" \
  --output "$CURATED_GOLD"

GOLD_SAMPLE="$GOLD_SAMPLE" REVIEW_CSV="$REVIEW_CSV" CURATED_GOLD="$CURATED_GOLD" python3 - <<'PY'
import csv
import json
import os
from pathlib import Path

sample = json.loads(Path(os.environ["GOLD_SAMPLE"]).read_text(encoding="utf-8"))
curated = json.loads(Path(os.environ["CURATED_GOLD"]).read_text(encoding="utf-8"))
with Path(os.environ["REVIEW_CSV"]).open("r", encoding="utf-8-sig", newline="") as handle:
    review_rows = list(csv.DictReader(handle))
payload = {
    "gold_sample": os.environ["GOLD_SAMPLE"],
    "review_csv": os.environ["REVIEW_CSV"],
    "curated_gold": os.environ["CURATED_GOLD"],
    "sample_cases": len(sample.get("cases", [])),
    "review_rows": len(review_rows),
    "curated_cases": len(curated.get("cases", [])),
}
print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
PY

echo "Curated model-eval gold set written: $CURATED_GOLD"
