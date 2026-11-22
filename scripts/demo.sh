#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
demo="${1:-a-call-before-rain}"
case "$demo" in
  a-call-before-rain|the-early-train) ;;
  *) echo "Choose a-call-before-rain or the-early-train" >&2; exit 2 ;;
esac
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
.venv/bin/python -m timeless "samples/$demo.md" "out/$demo.m4b" --cast "samples/$demo.cast.json"
