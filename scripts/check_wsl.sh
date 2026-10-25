#!/usr/bin/env bash
set -eu
pwd
command -v python3
command -v uv || true
python3 -c 'import importlib.util; print(importlib.util.find_spec("torch"))'
nvidia-smi --query-gpu=index,name,memory.used --format=csv,noheader
df -h /
