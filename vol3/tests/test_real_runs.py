"""vol3/runs/real_runs.py on the stub: one log per chapter and an ungraded sheet."""
import csv
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
with tempfile.TemporaryDirectory() as d:
    env = {k: v for k, v in os.environ.items() if k != "AIEV_MODEL"}
    env["AIEV_RUNS_DIR"] = d
    subprocess.run([sys.executable, "vol3/runs/real_runs.py"], cwd=ROOT, env=env, check=True,
                   stdout=subprocess.DEVNULL)
    names = sorted(p.name for p in Path(d).iterdir())
    for ch in ("ch10", "ch11", "ch13", "ch14", "ch15", "ch16"):
        assert any(f"-stub-{ch}-real.txt" in n for n in names), (ch, names)
    sheet = next(Path(d).glob("*-grading-sheet.csv"))
    rows = list(csv.DictReader(sheet.open()))
    assert len([r for r in rows if r["chapter"] == "11"]) == 6 * 4 * 2
    assert all(r["grade"] == "" for r in rows)        # never auto-graded
    assert all(r["reply"] and r["needed_passages"] for r in rows)
print("test_real_runs: ok")
