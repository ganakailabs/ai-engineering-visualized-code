#!/usr/bin/env bash
# D8 re-run (Nov 2026): Ch 11 k-sweep, Ch 16 held-out suite and the capstone on the Mac,
# after the vol3 audit fixes. Run from the repo root with Ollama serving llama3.2.
#
#   ollama pull llama3.2 && ollama serve      # once, in another terminal
#   bash vol3/runs/mac_rerun.sh
#
# Writes dated logs and blank grading sheets into vol3/runs/. Nothing is graded here:
# grade the sheets by hand (see README "Re-run after the Nov 2026 audit fixes").
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
D=$(date +%F)
R=vol3/runs
{
  echo "date=$D commit=$(git rev-parse --short HEAD) branch=$(git rev-parse --abbrev-ref HEAD)"
  sw_vers 2>/dev/null || uname -a
  python3 --version
  ollama --version
  ollama list | grep llama3.2
} > "$R/$D-run-env.txt"

env -u AIEV_MODEL python3 vol3/run_solutions.py > "$R/$D-stub-suite.txt"   # stub suite must pass first
export AIEV_MODEL=ollama:llama3.2
AIEV_KS=2,3,4,5,6,7,8,9,10 python3 vol3/runs/grading/ch11_k_sweep.py
python3 vol3/runs/real_runs.py ch16          # writes $D-llama3.2-ch16-real.txt and the ch16 sheet
python3 vol3/runs/pipeline_real.py
echo "done: logs in $R dated $D"
