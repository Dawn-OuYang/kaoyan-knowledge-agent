#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

run_experiment() {
  local name="$1"
  local task_queue="$2"
  local memory_reuse="$3"
  local affinity="$4"
  local allocator="$5"

  echo "===== ${name} ====="
  EXPERIMENT_NAME="${name}" \
  CONFIG_PATH="${PROJECT_ROOT}/ascend/runtime/${name}.yaml" \
  TASK_QUEUE_ENABLE="${task_queue}" \
  MULTI_STREAM_MEMORY_REUSE="${memory_reuse}" \
  CPU_AFFINITY_CONF="${affinity}" \
  PYTORCH_NPU_ALLOC_CONF="${allocator}" \
  bash "${PROJECT_ROOT}/ascend/finetune_qwen35_kaoyan.sh"
}

run_experiment baseline 0 0 0 ""
run_experiment runtime-optimized 2 2 1 "expandable_segments:True"
run_experiment memory-optimized 2 2 1 "expandable_segments:True"

python "${PROJECT_ROOT}/scripts/compare_npu_experiments.py"
