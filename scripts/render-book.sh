#!/usr/bin/env bash
set -euo pipefail
if (( $# == 0 )); then
  echo "Usage: bash scripts/render-book.sh MANUSCRIPT [--pace 0.90] [--narrator deep-narrator] [--formats mp3 m4b mp4]" >&2
  exit 2
fi
if [[ ! -f "$1" ]]; then
  echo "The manuscript could not be found: $1" >&2
  exit 2
fi
manuscript="$(cd "$(dirname "$1")" && pwd)/$(basename "$1")"
shift
cd "$(dirname "${BASH_SOURCE[0]}")/.."
if [[ ! -x .venv/bin/python ]] || ! cmp -s requirements.txt .venv/timeless-requirements.txt; then
  bash scripts/bootstrap.sh
fi
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
filename="$(basename "$manuscript")"
.venv/bin/python -m timeless "$manuscript" "out/${filename%.*}.m4b" --pace 0.90 --formats mp3 m4b mp4 "$@"
