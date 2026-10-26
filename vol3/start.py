"""Before You Start: the assistant Vol 2 finished (vol3-start = Vol 2's final code).

Run from the repo root:  python3 vol3/start.py
Runs Vol 2's agentic retrieval on the mug ticket, unchanged, and counts what it can
read. Vol 3 keeps the search_knowledge contract and replaces what sits behind it.
"""
import importlib.util
from pathlib import Path

import _root  # noqa: F401

import agentic_rag as rag
from store import HANDBOOK

_spec = importlib.util.spec_from_file_location(
    "vol2_ch11", Path(__file__).resolve().parents[1] / "vol2" / "ch11.py")
vol2_ch11 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(vol2_ch11)


def run(echo=True):
    r = rag.agentic(vol2_ch11.MUGS, vol2_ch11.ASHA, vol2_ch11.stub_agent)
    if echo:
        print(f"  knowledge: {len(HANDBOOK)} handbook passages ({', '.join(HANDBOOK)})")
        print(f"  mug ticket: stop={r['reason']} cites={r['cites']}")
    return r


if __name__ == "__main__":
    print("The assistant so far (Vol 2 final, stub):")
    run()
