#!/usr/bin/env bash
set -euo pipefail

# Run from the MindSpeed-MM repository root after fine-tuning.
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HF_DIR="${HF_DIR:-/workspace/mnt/share/weights/Qwen3.5-0.8B}"
LOAD_DIR="${LOAD_DIR:-${PROJECT_ROOT}/ascend/runtime/runtime-optimized/checkpoints/release}"
SAVE_DIR="${SAVE_DIR:-${PROJECT_ROOT}/ascend/runtime/exported_hf}"

python checkpoint/convert_cli.py GenericDCPConverter dcp_to_hf \
  --load_dir "${LOAD_DIR}" \
  --save_dir "${SAVE_DIR}" \
  --model_assets_dir "${HF_DIR}"

echo "Exported fine-tuned HuggingFace weights to ${SAVE_DIR}"
