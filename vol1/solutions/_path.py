"""Lets a solution import the chapter modules from the folder above (vol1/)."""
import sys
from pathlib import Path

PARENT = str(Path(__file__).resolve().parent.parent)
if PARENT not in sys.path:
    sys.path.insert(0, PARENT)

# The checks test BEHAVIOUR, so they pass on the stub and on a decent real model.
# A few exact values only the scripted stub produces are checked when STUB is True.
import os  # noqa: E402

STUB = not os.environ.get("AIEV_MODEL", "").startswith("ollama:")
DECISIONS = ("approve", "deny", "escalate")
