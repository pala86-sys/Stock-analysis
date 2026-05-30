#!/usr/bin/env bash
set -euo pipefail

PY=""
if command -v python3 >/dev/null 2>&1; then
  PY=python3
elif command -v python >/dev/null 2>&1; then
  PY=python
else
  echo "Python interpreter not found" >&2
  exit 127
fi

exec "$PY" -m uvicorn web_app:app --host 0.0.0.0 --port "${PORT:-8000}"
