#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
LAB_ROOT="$(cd -- "${PROJECT_ROOT}/.." && pwd)"

VENV_DIR="${KAOYAN_VENV_DIR:-/workspace/kaoyan-venv}"
MODEL_PATH="${KAOYAN_MODEL_PATH:-/workspace/mnt/share/weights/Qwen3.5-0.8B}"
MODEL_NAME="${KAOYAN_MODEL_NAME:-Qwen3.5-0.8B}"
MODEL_HOST="${KAOYAN_MODEL_HOST:-127.0.0.1}"
MODEL_PORT="${KAOYAN_MODEL_PORT:-8000}"
APP_HOST="${KAOYAN_HOST:-127.0.0.1}"
APP_PORT="${KAOYAN_PORT:-7860}"
LOG_DIR="${KAOYAN_LOG_DIR:-${LAB_ROOT}/logs}"

if [[ ! -f "${VENV_DIR}/bin/activate" ]]; then
  echo "Virtual environment not found: ${VENV_DIR}" >&2
  exit 1
fi
if [[ ! -d "${MODEL_PATH}" ]]; then
  echo "Qwen3.5 model not found: ${MODEL_PATH}" >&2
  exit 1
fi

source "${VENV_DIR}/bin/activate"
source /usr/local/Ascend/ascend-toolkit/set_env.sh
mkdir -p "${LOG_DIR}"

stop_service() {
  local pid_file="$1"
  if [[ ! -f "${pid_file}" ]]; then
    return
  fi
  local pid
  pid="$(cat "${pid_file}")"
  if [[ "${pid}" =~ ^[0-9]+$ ]] && kill -0 "${pid}" 2>/dev/null; then
    kill "${pid}"
    for _ in $(seq 1 30); do
      if ! kill -0 "${pid}" 2>/dev/null; then
        break
      fi
      sleep 1
    done
  fi
}

wait_for_health() {
  local url="$1"
  local label="$2"
  for _ in $(seq 1 60); do
    if curl -fsS --max-time 5 "${url}" >/dev/null; then
      echo "${label}: ready"
      return
    fi
    sleep 5
  done
  echo "${label}: health check timed out" >&2
  return 1
}

stop_service "${LOG_DIR}/kaoyan-rag-npu-server.pid"
stop_service "${LOG_DIR}/qwen35-npu-server.pid"

nohup python "${PROJECT_ROOT}/ascend/qwen35_ascend_server.py" \
  --model-path "${MODEL_PATH}" \
  --model-name "${MODEL_NAME}" \
  --host "${MODEL_HOST}" \
  --port "${MODEL_PORT}" \
  > "${LOG_DIR}/qwen35-npu-server.log" 2>&1 &
echo $! > "${LOG_DIR}/qwen35-npu-server.pid"

wait_for_health "http://${MODEL_HOST}:${MODEL_PORT}/health" "Qwen3.5 Ascend service"

export KAOYAN_MODEL_ENDPOINT="http://${MODEL_HOST}:${MODEL_PORT}/api/qwen/generate"
export KAOYAN_MODEL_PROTOCOL=qwen
export KAOYAN_MODEL_NAME="${MODEL_NAME}"
export KAOYAN_MODEL_TIMEOUT="${KAOYAN_MODEL_TIMEOUT:-180}"
export KAOYAN_MODEL_MAX_TOKENS="${KAOYAN_MODEL_MAX_TOKENS:-256}"
export KAOYAN_MODEL_TEMPERATURE="${KAOYAN_MODEL_TEMPERATURE:-0}"
export KAOYAN_HOST="${APP_HOST}"
export KAOYAN_PORT="${APP_PORT}"

nohup python "${PROJECT_ROOT}/src/server.py" \
  > "${LOG_DIR}/kaoyan-rag-npu-server.log" 2>&1 &
echo $! > "${LOG_DIR}/kaoyan-rag-npu-server.pid"

wait_for_health "http://${APP_HOST}:${APP_PORT}/api/health" "Kaoyan RAG service"
curl -fsS "http://${APP_HOST}:${APP_PORT}/api/health"
echo
