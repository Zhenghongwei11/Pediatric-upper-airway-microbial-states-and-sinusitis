#!/usr/bin/env bash
set -euo pipefail

export PERMUTATIONS="${PERMUTATIONS:-99}"
export BOOTSTRAP_ITERATIONS="${BOOTSTRAP_ITERATIONS:-100}"

echo "[1/1] Running data acquisition, analyses, and figure generation"
make figures

echo "Done. Key outputs are in results/ and plots/publication/."
