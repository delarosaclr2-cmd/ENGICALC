#!/usr/bin/env sh
cd "$(dirname "$0")"
[ -f .venv/bin/activate ] && . .venv/bin/activate
python3 main.py "$@"
