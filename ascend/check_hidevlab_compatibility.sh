#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MINDSPEED_MM_ROOT="${1:-$(cd "${PROJECT_ROOT}/.." && pwd)/MindSpeed-MM}"

# shellcheck disable=SC1091
source "${PROJECT_ROOT}/ascend/resolve_ascend_env.sh"
source_ascend_env

echo "===== HiDevLab runtime ====="
echo "architecture=$(uname -m)"
echo "python=$(python --version 2>&1)"
echo "python_path=$(command -v python)"
echo "mindspeed_mm_root=${MINDSPEED_MM_ROOT}"

echo "===== Package compatibility ====="
python - <<'PY'
import importlib
import platform

print(f"platform={platform.platform()}")
for name in (
    "torch",
    "torch_npu",
    "transformers",
    "datasets",
    "accelerate",
    "mindspeed",
    "mindspeed_mm",
):
    try:
        module = importlib.import_module(name)
        print(f"{name}={getattr(module, '__version__', 'available')}")
    except Exception as exc:
        print(f"{name}=UNAVAILABLE: {type(exc).__name__}: {exc}")

import torch
import torch_npu

print(f"npu_available={torch_npu.npu.is_available()}")
print(f"npu_count={torch.npu.device_count()}")
x = torch.arange(5, dtype=torch.float32).npu()
print(f"npu_result={(x * 2).cpu().tolist()}")
PY

echo "===== Bundled MindSpeed-MM source ====="
test -f "${MINDSPEED_MM_ROOT}/pyproject.toml"
test -f "${MINDSPEED_MM_ROOT}/mindspeed_mm/fsdp/train/trainer.py"
test -f "${MINDSPEED_MM_ROOT}/examples/qwen3_5/qwen3_5_0.8B_config.yaml"
echo "MindSpeed-MM source layout: PASS"

echo "===== Project shell syntax ====="
for script in "${PROJECT_ROOT}"/ascend/*.sh; do
  bash -n "${script}"
done
echo "Shell syntax: PASS"

echo "Compatibility inspection complete. No packages or model weights were installed."
