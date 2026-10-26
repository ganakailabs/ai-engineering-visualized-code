"""Put Vol 2 (../vol2) and Vol 1 (../vol1) on the path, behind vol3/.

Vol 2 modules do `import _root`; with vol3/ first on the path they get this file, so
it also does Vol 2's job: Vol 1 on the path and Vol 2's redirect for the Vol 1 chapter
names (ch12, ch13, ch15) that Vol 1 and Vol 2 modules import from each other.
"""
import runpy
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
for p in (REPO / "vol1", REPO / "vol2"):          # ends as vol3, vol2, vol1
    if str(p) not in sys.path:
        sys.path.insert(1, str(p))
runpy.run_path(str(REPO / "vol2" / "_root.py"))   # installs the Vol 1 chapter redirect
