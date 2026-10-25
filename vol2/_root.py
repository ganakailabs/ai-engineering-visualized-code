"""Put the Vol 1 folder (../vol1: store.py, parse.py, ...) on the path."""
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "vol1"   # repo/vol1, next to repo/vol2
if str(ROOT) not in sys.path:
    sys.path.insert(1, str(ROOT))


VOL1_ONLY = {"ch12", "ch13", "ch15"}  # Vol 1 ch13 does `from ch12 import cosine`;
                              # Vol 2 mcp_host does `from ch13 import hybrid`;
                              # Vol 2 agentic_rag does `from ch15 import index`


class _Vol1Chapters:
    """`import ch12` means Vol 1's ch12.py (cosine, used by Vol 1 ch13's hybrid
    search), not Vol 2's ch12.py script, which sits first on the path. Only the names
    Vol 1 modules import from each other are redirected; Vol 2 tests still import
    Vol 2 chapters (ch11, ...) by name."""

    @staticmethod
    def find_spec(name, path=None, target=None):
        if path is None and name in VOL1_ONLY and (ROOT / f"{name}.py").exists():
            return importlib.util.spec_from_file_location(name, ROOT / f"{name}.py")
        return None


if not any(isinstance(f, _Vol1Chapters) or f is _Vol1Chapters for f in sys.meta_path):
    sys.meta_path.insert(0, _Vol1Chapters)
