"""Let a solution import the chapter code: vol3/, then ../vol2, then ../vol1 on the path."""
import sys
from pathlib import Path

V3 = Path(__file__).resolve().parents[1]
for p in (V3.parent / "vol1", V3.parent / "vol2", V3):  # vol3 first: its ch01.py is not Vol 2's
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import _root  # noqa: E402,F401  (Vol 2's Vol 1 redirect)
import llm  # noqa: E402

STUB = llm.name() == "stub"     # exact traces are asserted on the stub only
