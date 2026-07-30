#!/usr/bin/env bash
# WARDEN — one-command launcher for the local hero path.
# Usage:
#   ./run.sh test     run the acceptance suite (pytest)
#   ./run.sh eval      run the offline eval over 50 attacks -> the 3 numbers
#   ./run.sh demo      run the 4-minute demo in the terminal
#   ./run.sh ui        (re)build console data + serve the React console
#   ./run.sh all       test + eval + demo, then serve the UI   (default)
set -euo pipefail
cd "$(dirname "$0")"

# Prefer a locally-installed Node if present (see README).
export PATH="$HOME/.local/node/bin:$PATH"

py() { python3 "$@"; }

build_data() { py demo/build_ui_data.py >/dev/null && echo "  console data regenerated from the live pipeline"; }

case "${1:-all}" in
  test) py -m pytest -q ;;
  eval) py -m eval.harness ;;
  demo) py -m demo.run_demo ;;
  synth) ( cd infra && cdk synth ) ;;   # AWS mode: prove the stack + IAM grants
  ui)
    build_data
    ( cd ui && npm install --silent >/dev/null 2>&1 || true && npm run build && npm run preview )
    ;;
  all)
    echo "== acceptance suite =="; py -m pytest -q
    echo; echo "== offline eval =="; py -m eval.harness
    echo; echo "== 4-minute demo =="; py -m demo.run_demo
    echo; echo "== console =="; build_data
    ( cd ui && npm install --silent >/dev/null 2>&1 || true && npm run build && npm run preview )
    ;;
  *) echo "unknown target: $1 (use test|eval|demo|ui|all)"; exit 1 ;;
esac
