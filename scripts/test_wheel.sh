#!/usr/bin/env bash
# Install the built wheel into a fresh virtual environment: no dependencies may come with it, the guard modules
# import and the console script runs. Works in Git Bash on Windows and in Linux/macOS shells.
#   bash scripts/test_wheel.sh [python-executable]
set -euo pipefail
PY=${1:-python3}
ROOT=$(cd "$(dirname "$0")/.." && pwd)
WHL=$(ls -t "$ROOT"/dist/baby_boon-*.whl | head -1)
TMP=$(mktemp -d)
echo "venv in $TMP with $($PY --version 2>&1)"
"$PY" -m venv "$TMP/venv"
if [ -x "$TMP/venv/bin/python" ]; then VPY="$TMP/venv/bin/python"; BIN="$TMP/venv/bin"; else VPY="$TMP/venv/Scripts/python.exe"; BIN="$TMP/venv/Scripts"; fi
"$VPY" -m pip install -q "$WHL"
cd "$TMP"
EXTRA=$("$VPY" -m pip list --format=freeze --exclude-editable | grep -v -i -E "^(pip|setuptools|baby-boon|baby_boon)==" || true)
if [ -n "$EXTRA" ]; then echo "unexpected dependencies installed: $EXTRA"; exit 1; fi
"$VPY" -c "from baby_boon import chat, guard, health, facts, local; print('guard ok:', guard.guarded(lambda a: {'text': 'Sure.', 'tone': 'warm', 'expression': 'smile', 'intensity': 1, 'cue_valid': True}, 1, 'hi')['text'])"
"$BIN/baby-boon" --help
