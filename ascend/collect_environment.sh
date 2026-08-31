#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUTPUT_DIR="${OUTPUT_DIR:-${PROJECT_ROOT}/reports/npu_raw}"
OUTPUT_FILE="${OUTPUT_FILE:-${OUTPUT_DIR}/environment.txt}"
mkdir -p "${OUTPUT_DIR}"

{
  echo "collected_at=$(date --iso-8601=seconds 2>/dev/null || date)"
  echo "hostname=$(hostname)"
  echo "working_directory=$(pwd)"
  echo "kernel=$(uname -a)"
  echo "ASCEND_HOME_PATH=${ASCEND_HOME_PATH:-}"
  echo "ASCEND_TOOLKIT_HOME=${ASCEND_TOOLKIT_HOME:-}"
  echo "PATH=${PATH}"
  echo
  echo "===== npu-smi info ====="
  if command -v npu-smi >/dev/null 2>&1; then
    npu-smi info
  else
    echo "npu-smi not found"
  fi
  echo
  echo "===== Python runtime ====="
  command -v python || true
  python --version 2>&1 || true
  python - <<'PY'
import importlib
import platform

print(f"platform={platform.platform()}")
for name in ("torch", "torch_npu", "transformers", "mindspeed_mm"):
    try:
        module = importlib.import_module(name)
        print(f"{name}={getattr(module, '__version__', 'available')}")
    except Exception as exc:
        print(f"{name}=UNAVAILABLE: {exc}")
PY
  echo
  echo "===== CANN candidates ====="
  for path in \
    /usr/local/Ascend/cann/set_env.sh \
    /usr/local/Ascend/cann-9.0.0/set_env.sh \
    /usr/local/Ascend/ascend-toolkit/set_env.sh \
    /usr/local/Ascend/ascend-toolkit/latest/set_env.sh; do
    if [ -e "${path}" ]; then
      echo "FOUND ${path}"
    fi
  done
} | tee "${OUTPUT_FILE}"

echo "Environment evidence saved to ${OUTPUT_FILE}"
