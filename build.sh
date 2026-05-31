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

FONT="assets/fonts/NotoSansTC-Regular.ttf"
if [[ ! -f "$FONT" ]]; then
  mkdir -p assets/fonts
  curl -fsSL -o "$FONT" \
    "https://fonts.gstatic.com/s/notosanstc/v39/-nFuOG829Oofr2wohFbTp9ifNAn722rq0MXz76Cy_Co.ttf"
fi

FONT_OTF="assets/fonts/NotoSansTC-Regular.otf"
if [[ ! -f "$FONT_OTF" ]]; then
  mkdir -p assets/fonts
  curl -fsSL -o "$FONT_OTF" \
    "https://raw.githubusercontent.com/notofonts/noto-cjk/main/Sans/SubsetOTF/TC/NotoSansTC-Regular.otf"
fi

pip install --upgrade pip
pip install -r requirements-web.txt
