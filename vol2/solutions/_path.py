"""Let a solution import the chapter code: vol2/ and ../vol1 go on the path."""
import sys
from pathlib import Path

V2 = Path(__file__).resolve().parents[1]
for p in (V2.parent / "vol1", V2):  # vol2 first: its ch01.py is not Vol 1's
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import llm  # noqa: E402

STUB = llm.name() == "stub"     # exact traces are asserted on the stub only
