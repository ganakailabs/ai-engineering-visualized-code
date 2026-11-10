"""Let this file import the chapter code: vol4/ first; vol4/_root.py adds vol3, vol2, vol1."""
import sys
from pathlib import Path

V4 = Path(__file__).resolve().parents[1]
if str(V4) not in sys.path:
    sys.path.insert(0, str(V4))

import _root  # noqa: E402,F401
