#!/usr/bin/env bash
set -euo pipefail

if [[ ! -f ".venv/bin/activate" ]]; then
  echo "Missing .venv — run build.sh first" >&2
  exit 127
fi

source .venv/bin/activate
exec uvicorn web_app:app --host 0.0.0.0 --port "${PORT:-8000}"
