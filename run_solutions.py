"""Run every exercise solution in solutions/, each in its own process, the way a reader
runs it. Each solution asserts its own result, so a non-zero exit means a solution no
longer matches the book. No API key needed."""
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
env = dict(os.environ)
if env.pop("AIEV_MODEL", None):       # the asserts check the stub's output
    print("note: AIEV_MODEL ignored here; solutions are checked on the stub")
failed = []
paths = sorted((HERE / "solutions").glob("ch*_solution.py"))
paths += sorted((HERE / "tests").glob("test_*.py"))
for path in paths:
    print(f"===== {path.parent.name}/{path.name} =====", flush=True)
    if subprocess.call([sys.executable, str(path)], cwd=HERE, env=env) != 0:
        failed.append(path.name)
print(f"\nsolutions FAILED: {', '.join(failed)}" if failed else "\nsolutions: all passed")
sys.exit(1 if failed else 0)
