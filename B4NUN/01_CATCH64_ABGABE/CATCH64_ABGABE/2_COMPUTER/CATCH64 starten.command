#!/bin/sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$SCRIPT_DIR"

if [ ! -x ".venv/bin/python" ]; then
    echo "CATCH 64 wird einmalig eingerichtet ..."
    python3 -m venv .venv
    .venv/bin/python -m pip install -r requirements.txt
fi

exec .venv/bin/python catch64.py

