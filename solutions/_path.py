"""Lets a solution import the chapter modules from the folder above (code/support-assistant/)."""
import sys
from pathlib import Path

PARENT = str(Path(__file__).resolve().parent.parent)
if PARENT not in sys.path:
    sys.path.insert(0, PARENT)
