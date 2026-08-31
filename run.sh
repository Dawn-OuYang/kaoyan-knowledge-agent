#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${PROJECT_ROOT}"

if command -v python3 >/dev/null 2>&1; then
  exec python3 src/server.py
fi
if command -v python >/dev/null 2>&1; then
  exec python src/server.py
fi

echo "Python 3 was not found. Install Python 3.10+ and rerun ./run.sh." >&2
exit 1
