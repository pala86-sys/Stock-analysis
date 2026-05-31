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

"$PY" -m venv .venv
source .venv/bin/activate

pip install --upgrade pip
pip install -r requirements-web.txt
