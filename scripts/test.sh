#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/backend"
python -m pytest -q
cd "$ROOT/frontend"
node --test tests/visual.test.ts
