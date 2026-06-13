#!/usr/bin/env bash
set -euo pipefail

PROVIDER=${PROVIDER:-qwen-mt}

python3 - <<'PY'
import importlib.util
import json
import os
import sys

provider = os.environ.get("PROVIDER", "qwen-mt")

requirements = {
    "dry-run": {"keys": [], "package": None},
    "openai": {"keys": ["OPENAI_API_KEY"], "package": "openai"},
    "openai-chat": {"keys": ["OPENAI_COMPATIBLE_API_KEY"], "package": "openai"},
    "qwen-mt": {"keys": ["DASHSCOPE_API_KEY", "QWEN_API_KEY"], "package": "openai"},
}

base_provider = provider.split(":", 1)[0]
config = requirements.get(base_provider)
if config is None:
    print(json.dumps({"provider": provider, "ready": False, "error": f"unknown provider: {provider}"}, sort_keys=True))
    raise SystemExit(2)

package = config["package"]
package_ready = True if package is None else importlib.util.find_spec(package) is not None
key_names = config["keys"]
present_keys = [key for key in key_names if os.environ.get(key)]
key_ready = not key_names or bool(present_keys)
ready = package_ready and key_ready

payload = {
    "provider": provider,
    "ready": ready,
    "package": package or "",
    "package_ready": package_ready,
    "required_key_any_of": key_names,
    "present_key_names": present_keys,
}
print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
if not ready:
    if package and not package_ready:
        print(f"missing package: install with `python3 -m pip install '.[openai]'`", file=sys.stderr)
    if key_names and not present_keys:
        print(f"missing API key: set one of {', '.join(key_names)}", file=sys.stderr)
    raise SystemExit(1)
PY
