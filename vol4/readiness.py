"""Chapter 1: MM-119 The Readiness Map.

A box on the whole diagram is ready when it has a named owner in
docs/release-manifest.json; the LAB checklist is complete when every box is ticked and
the starter documents exist. That is necessary groundwork, not evidence that any
deployment control (identity, TLS, supervision, health, persistence, secrets) was
exercised. A demo score ticks none of these boxes.
"""
import json
from pathlib import Path

DOCS = Path(__file__).resolve().parent / "docs"


def check(docs, drop=()):
    manifest = json.loads((docs / "release-manifest.json").read_text())
    ticks = {}
    for box, spec in manifest["components"].items():
        ticks[box] = bool(spec.get("owner")) and box not in drop
    for name in manifest["documents"]:
        p = docs / name
        ticks[name] = p.exists() and p.stat().st_size > 0 and name not in drop
    ticks["release_id"] = bool(manifest.get("release_id"))
    return ticks


def report(docs, drop=()):
    ticks = check(docs, drop)
    missing = [k for k, ok in ticks.items() if not ok]
    lines = [f"readiness {sum(ticks.values())}/{len(ticks)} ticked"]
    lines.append("missing: " + ", ".join(missing) + " -> not ready" if missing
                 else "missing: none -> lab checklist complete (not deployment evidence)")
    return lines
