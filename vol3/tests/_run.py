"""Run every test_* function in the calling module and print '<name>: OK'."""
import sys


def run_all(name):
    mod = sys.modules["__main__"]
    for k in sorted(k for k in vars(mod) if k.startswith("test_")):
        getattr(mod, k)()
    print(f"{name}: OK")
