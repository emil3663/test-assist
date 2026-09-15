#!/usr/bin/env bash
# Test Assist - launch the PySide6 desktop app (macOS and Linux)
#
# The macOS/Linux counterpart to run.ps1. Prefers a .venv alongside the
# repo if one exists - PySide6 is a large dependency that most people
# would rather not install into the system interpreter, and on macOS the
# system python3 is managed by Apple and cannot be pip-installed into at
# all.
set -euo pipefail
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$script_dir"

venv_python="$script_dir/../.venv/bin/python"
if [ -x "$venv_python" ]; then
    exec "$venv_python" main.py "$@"
fi

exec python3 main.py "$@"
