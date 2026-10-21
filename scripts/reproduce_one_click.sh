#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
make all PYTHON="${PYTHON:-python3}"
