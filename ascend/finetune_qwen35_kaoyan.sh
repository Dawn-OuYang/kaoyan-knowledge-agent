#!/usr/bin/env bash
set -euo pipefail

# Run from the MindSpeed-MM repository root on an Ascend server.
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck disable=SC1091
source "${PROJECT_ROOT}/ascend/resolve_ascend_env.sh"
source_ascend_env

export NON_MEGATRON=true
export MULTI_STREAM_MEMORY_REUSE="${MULTI_STREAM_MEMORY_REUSE:-2}"
export TASK_QUEUE_ENABLE="${TASK_QUEUE_ENABLE:-2}"
export ASCEND_LAUNCH_BLOCKING="${ASCEND_LAUNCH_BLOCKING:-0}"
export ACLNN_CACHE_LIMIT="${ACLNN_CACHE_LIMIT:-100000}"
export CPU_AFFINITY_CONF="${CPU_AFFINITY_CONF:-1}"
ALLOCATOR_CONF="${PYTORCH_NPU_ALLOC_CONF-expandable_segments:True}"
if [ -n "${ALLOCATOR_CONF}" ]; then
  export PYTORCH_NPU_ALLOC_CONF="${ALLOCATOR_CONF}"
else
  unset PYTORCH_NPU_ALLOC_CONF || true
fi

NPUS_PER_NODE="${NPUS_PER_NODE:-1}"
MASTER_ADDR="${MASTER_ADDR:-localhost}"
MASTER_PORT="${MASTER_PORT:-6000}"
NNODES="${NNODES:-1}"
NODE_RANK="${NODE_RANK:-0}"
WORLD_SIZE=$((NPUS_PER_NODE * NNODES))
export WORLD_SIZE

DISTRIBUTED_ARGS=(
  --nproc_per_node "${NPUS_PER_NODE}"
  --nnodes "${NNODES}"
  --node_rank "${NODE_RANK}"
  --master_addr "${MASTER_ADDR}"
  --master_port "${MASTER_PORT}"
)

EXPERIMENT_NAME="${EXPERIMENT_NAME:-runtime-optimized}"
CONFIG_PATH="${CONFIG_PATH:-${PROJECT_ROOT}/ascend/runtime/${EXPERIMENT_NAME}.yaml}"
LOG_DIR="${LOG_DIR:-${PROJECT_ROOT}/reports/npu_raw}"
mkdir -p "${LOG_DIR}"

if [ ! -f "${CONFIG_PATH}" ]; then
  echo "ERROR: rendered config not found: ${CONFIG_PATH}" >&2
  echo "Run: python ${PROJECT_ROOT}/ascend/prepare_ascend_run.py --help" >&2
  exit 1
fi

LOGFILE="${LOG_DIR}/${EXPERIMENT_NAME}_$(date +%Y%m%d_%H%M%S).log"
echo "EXPERIMENT_NAME=${EXPERIMENT_NAME}" | tee "${LOGFILE}"
echo "config=${CONFIG_PATH}" | tee -a "${LOGFILE}"
echo "TASK_QUEUE_ENABLE=${TASK_QUEUE_ENABLE}" | tee -a "${LOGFILE}"
echo "MULTI_STREAM_MEMORY_REUSE=${MULTI_STREAM_MEMORY_REUSE}" | tee -a "${LOGFILE}"
echo "CPU_AFFINITY_CONF=${CPU_AFFINITY_CONF}" | tee -a "${LOGFILE}"

torchrun "${DISTRIBUTED_ARGS[@]}" mindspeed_mm/fsdp/train/trainer.py \
  "${CONFIG_PATH}" \
  2>&1 | tee -a "${LOGFILE}"

python "${PROJECT_ROOT}/scripts/parse_mindspeed_log.py" "${LOGFILE}"
echo "Training log saved to ${LOGFILE}"
