#!/usr/bin/env bash
set -euo pipefail

WORK_DIR=${WORK_DIR:-build/current-model-eval}
GOLD_PATH=${GOLD_PATH:-$WORK_DIR/gold-curated.json}
ALLOW_UNCURATED=${ALLOW_UNCURATED:-0}
PROVIDERS=${PROVIDERS:-baseline=dry-run}
REPORT_PATH=${REPORT_PATH:-$WORK_DIR/eval-compare-report.json}
CANDIDATE_CACHE=${CANDIDATE_CACHE:-$WORK_DIR/eval-candidates.json}
REQUEST_LOG=${REQUEST_LOG:-$WORK_DIR/eval-compare-requests.jsonl}
MIN_SIMILARITY=${MIN_SIMILARITY:-0.75}
FAIL_UNDER=${FAIL_UNDER:-0}
CHECK_PROVIDER_ENV=${CHECK_PROVIDER_ENV:-1}

if [[ ! -f "$GOLD_PATH" ]]; then
  if [[ "$ALLOW_UNCURATED" == "1" && -f "$WORK_DIR/gold-sample.json" ]]; then
    GOLD_PATH="$WORK_DIR/gold-sample.json"
    echo "Using uncurated gold sample for pipeline verification: $GOLD_PATH"
  else
    echo "curated gold does not exist: $GOLD_PATH" >&2
    echo "Run make prepare-current-model-eval, approve build/current-model-eval/gold-review/review.csv, then run eval apply-review." >&2
    exit 1
  fi
fi

read -r -a provider_specs <<< "$PROVIDERS"
if [[ "${#provider_specs[@]}" -eq 0 ]]; then
  echo "no providers configured" >&2
  exit 1
fi

provider_args=()
for provider_entry in "${provider_specs[@]}"; do
  provider_args+=(--provider "$provider_entry")
  provider_spec="$provider_entry"
  if [[ "$provider_spec" == *"="* ]]; then
    provider_spec="${provider_spec#*=}"
  fi
  if [[ "$CHECK_PROVIDER_ENV" == "1" ]]; then
    PROVIDER="$provider_spec" bash scripts/check-provider-env.sh
  fi
done

python3 -m limbus_translate.cli eval compare \
  --gold "$GOLD_PATH" \
  "${provider_args[@]}" \
  --candidate-cache "$CANDIDATE_CACHE" \
  --request-log "$REQUEST_LOG" \
  --report "$REPORT_PATH" \
  --min-similarity "$MIN_SIMILARITY" \
  --fail-under "$FAIL_UNDER"

REPORT_PATH="$REPORT_PATH" GOLD_PATH="$GOLD_PATH" PROVIDERS="$PROVIDERS" python3 - <<'PY'
import json
import os
from pathlib import Path

report_path = Path(os.environ["REPORT_PATH"])
report = json.loads(report_path.read_text(encoding="utf-8"))
summary = report.get("summary", {})
rankings = summary.get("rankings", [])
case_count = summary.get("cases") or summary.get("total")
if case_count is None and rankings:
    case_count = rankings[0].get("total")
payload = {
    "gold": os.environ["GOLD_PATH"],
    "providers": os.environ["PROVIDERS"],
    "report": str(report_path),
    "cases": case_count,
    "provider_count": summary.get("providers"),
    "best_provider": rankings[0].get("provider") if rankings else None,
    "best_pass_rate": rankings[0].get("pass_rate") if rankings else None,
}
print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
PY

echo "Model comparison complete: $REPORT_PATH"
