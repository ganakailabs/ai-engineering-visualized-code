"""Put Vol 3 (../vol3), Vol 2 (../vol2) and Vol 1 (../vol1) on the path, behind vol4/.

Vol 4 reuses the earlier volumes unchanged: Vol 2's ledger and courier server, Vol 1's
store fixtures and token counter. Vol 3's _root.py installs Vol 2's redirect for the
Vol 1 chapter names, so this file runs it rather than repeating it.
AIEV_CODE may point at another checkout that holds vol1/ ... vol3/ (used while the
book is drafted outside the companion repo); by default it is this repo.
"""
import os
import runpy
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = Path(os.environ.get("AIEV_CODE") or HERE.parent)
for p in (REPO / "vol1", REPO / "vol2", REPO / "vol3"):   # ends as vol4, vol3, vol2, vol1
    if str(p) not in sys.path:
        sys.path.insert(1, str(p))
runpy.run_path(str(REPO / "vol3" / "_root.py"))          # Vol 1 / Vol 2 path and redirect
