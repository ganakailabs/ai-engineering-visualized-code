"""Run every chapter's demo, then every exercise solution. No API key needed."""
import runpy
import subprocess
import sys
from pathlib import Path

for ch in [f"ch{n:02d}" for n in range(1, 13)]:
    print(f"===== {ch} =====")
    runpy.run_module(ch, run_name="__main__")

# The exercise solutions assert their own results (see run_solutions.py).
sys.exit(subprocess.call([sys.executable, str(Path(__file__).resolve().parent / "run_solutions.py")]))
