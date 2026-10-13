"""Run every exercise solution in solutions/, each in its own process, the way a reader
runs it. Each solution asserts its own result, so a non-zero exit means a solution no
longer matches the book. No API key needed."""
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
failed = []
for path in sorted((HERE / "solutions").glob("ch*_solution.py")):
    print(f"===== solutions/{path.name} =====", flush=True)
    if subprocess.call([sys.executable, str(path)], cwd=HERE) != 0:
        failed.append(path.name)
print(f"\nsolutions FAILED: {', '.join(failed)}" if failed else "\nsolutions: all passed")
sys.exit(1 if failed else 0)
