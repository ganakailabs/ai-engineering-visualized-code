"""Run every Vol 3 solution and implementation test, each in its own process.

    python3 vol3/run_solutions.py          # the stub (default): exact asserts
    AIEV_MODEL=ollama:llama3.2 python3 vol3/run_solutions.py --real
        # solutions against a real model: behaviour asserts only; tests stay on the stub
"""
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
real = "--real" in sys.argv
stub_env = {k: v for k, v in os.environ.items() if k != "AIEV_MODEL"}
if os.environ.get("AIEV_MODEL") and not real:
    print("note: AIEV_MODEL ignored here; add --real to run the solutions on it")
failed = []
for path in sorted((HERE / "solutions").glob("ch*_solution.py")) + \
        sorted((HERE / "tests").glob("test_*.py")):
    env = dict(os.environ) if real and path.parent.name == "solutions" else stub_env
    print(f"===== {path.parent.name}/{path.name} "
          f"(model={env.get('AIEV_MODEL', 'stub')}) =====", flush=True)
    if subprocess.call([sys.executable, str(path)], cwd=HERE.parent, env=env) != 0:
        failed.append(path.name)
print(f"\nFAILED: {', '.join(failed)}" if failed else "\nall passed")
sys.exit(1 if failed else 0)
