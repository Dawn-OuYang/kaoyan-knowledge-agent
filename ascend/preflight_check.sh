#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck disable=SC1091
source "${PROJECT_ROOT}/ascend/resolve_ascend_env.sh"
if ! ASCEND_ENV="$(resolve_ascend_env)"; then
  ASCEND_ENV="CANN_ENV_NOT_FOUND"
fi
HF_DIR="${HF_DIR:-/workspace/mnt/share/weights/Qwen3.5-0.8B}"
DCP_DIR="${DCP_DIR:-/workspace/mnt/share/weights/Qwen3.5-0.8B-dcp}"
CHECK_STAGE="${CHECK_STAGE:-pre-convert}"

failures=0
check_path() {
  local label="$1"
  local path="$2"
  if [ -e "${path}" ]; then
    echo "PASS ${label}: ${path}"
  else
    echo "FAIL ${label}: ${path}"
    failures=$((failures + 1))
  fi
}

check_path "CANN environment" "${ASCEND_ENV}"
check_path "HuggingFace model" "${HF_DIR}"
if [ "${CHECK_STAGE}" = "post-convert" ]; then
  check_path "DCP model" "${DCP_DIR}"
else
  echo "SKIP DCP model before weight conversion: ${DCP_DIR}"
fi
check_path "SFT dataset" "${PROJECT_ROOT}/ascend/annotations_slim.json"
check_path "MindSpeed-MM trainer" "mindspeed_mm/fsdp/train/trainer.py"

if command -v npu-smi >/dev/null 2>&1; then
  echo "PASS npu-smi"
  npu-smi info
else
  echo "FAIL npu-smi not found"
  failures=$((failures + 1))
fi

python - <<'PY'
import importlib
import sys

modules = ["torch", "torch_npu", "transformers", "mindspeed_mm"]
failed = []
for name in modules:
    try:
        module = importlib.import_module(name)
        print(f"PASS import {name}: {getattr(module, '__version__', 'available')}")
    except Exception as exc:
        failed.append(name)
        print(f"FAIL import {name}: {exc}")
if failed:
    sys.exit(1)
PY

if [ "${failures}" -ne 0 ]; then
  echo "Preflight failed with ${failures} filesystem/runtime checks." >&2
  exit 1
fi
echo "Ascend preflight passed."
