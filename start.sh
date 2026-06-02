#!/usr/bin/env bash
set -euo pipefail

echo "[start] $(date -u +%Y-%m-%dT%H:%M:%SZ) boot"

if [[ ! -f ".venv/bin/activate" ]]; then
  echo "Missing .venv — run build.sh first" >&2
  exit 127
fi

source .venv/bin/activate

export MPLBACKEND=Agg
export PYTHONUNBUFFERED=1

PORT="${PORT:-8000}"
echo "[start] uvicorn web_app:app host=0.0.0.0 port=${PORT}"

exec uvicorn web_app:app --host 0.0.0.0 --port "${PORT}" --log-level info
