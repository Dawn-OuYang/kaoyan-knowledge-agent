#!/usr/bin/env bash
set -euo pipefail

# Run this script from the MindSpeed-MM repository root on an Ascend server.
# Adjust the two paths if the model weights are stored elsewhere.
HF_DIR="${HF_DIR:-/workspace/mnt/share/weights/Qwen3.5-0.8B}"
DCP_DIR="${DCP_DIR:-/workspace/mnt/share/weights/Qwen3.5-0.8B-dcp}"

python checkpoint/convert_cli.py GenericDCPConverter hf_to_dcp \
  --hf_dir "${HF_DIR}" \
  --dcp_dir "${DCP_DIR}"

echo "Converted HuggingFace weights to DCP:"
echo "  HF_DIR=${HF_DIR}"
echo "  DCP_DIR=${DCP_DIR}"
