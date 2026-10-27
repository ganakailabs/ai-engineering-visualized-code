"""Read the page: layout-aware parsing, tables as rows, OCR flags (Vol 3 Chapter 3).

The fixture in vol3/knowledge/layout/ is what a layout-aware parser hands back for a
fictional 5-page warranty sheet: typed blocks with columns, one table and one scanned
page. naive_text() reads the blocks the way a plain extractor does (stream order, table
flattened, footers kept); parse() keeps reading order, turns each table row into its own
record with the header attached, drops footers and flags low-confidence OCR text.
"""
import json
from pathlib import Path

import _root  # noqa: F401

import events
from events import Trace
from ingest import _Clock

FIXTURE = Path(__file__).resolve().parent / "knowledge" / "layout" / "nw-500-warranty.json"
OCR_FLOOR = 0.80            # below this, OCR text is flagged for a person to read
events.KINDS.update({"parse", "ocr"})            # Vol 3 (series contract section 4)


def load(path=FIXTURE):
    return json.loads(Path(path).read_text())


def naive_text(doc):
    """What a plain extractor gives: every block in stream order, tables as loose words."""
    words = []
    for p in doc["pages"]:
        for b in p["blocks"]:
            if b["type"] == "table":
                words += b["header"] + [cell for row in b["rows"] for cell in row]
            else:
                words.append(b["text"])
    return " ".join(words)


def row_text(header, row):
    return " | ".join(f"{h}: {v}" for h, v in zip(header, row))


def parse(doc, floor=OCR_FLOOR):
    """Elements in reading order: (page, kind, text, flags)."""
    out = []
    for p in doc["pages"]:
        text = [b for b in p["blocks"] if b["type"] == "text"]
        for b in p["blocks"]:
            if b["type"] == "heading":
                out.append({"page": p["page"], "kind": "heading", "text": b["text"]})
            elif b["type"] == "table":
                for r in b["rows"]:
                    out.append({"page": p["page"], "kind": "row", "table": b["caption"],
                                "text": row_text(b["header"], r)})
        for col in sorted({b["col"] for b in text}):          # column 1, then column 2
            part = sorted((b for b in text if b["col"] == col), key=lambda b: b["line"])
            conf = min(b.get("ocr_conf", 1.0) for b in part)
            out.append({"page": p["page"], "kind": "text",
                        "text": " ".join(b["text"] for b in part),
                        "ocr_conf": conf, "flagged": conf < floor})
    return out


def chunks(doc, elements):
    """One chunk per element; a row chunk carries its table caption."""
    rows, seen = [], {}
    for e in elements:
        n = seen[e["page"]] = seen.get(e["page"], 0) + 1      # place on the page
        text = f"{e['table']}: {e['text']}" if e["kind"] == "row" else e["text"]
        rows.append({"id": f"{doc['source']}@{doc['version']}:p{e['page']}.e{n}",
                     "page": e["page"], "kind": e["kind"], "text": text,
                     "flagged": e.get("flagged", False)})
    return rows


def spotcheck(doc, elements):
    """Compare one element per sampled page with the hand-checked gold text."""
    ok = 0
    for page, want in doc["gold"].items():
        got = [e["text"] for e in elements if e["page"] == int(page)]
        ok += want in got
    return ok, len(doc["gold"])


def run(doc=None, echo=True, floor=OCR_FLOOR):
    doc = doc or load()
    t = Trace(_Clock(), "T-103", "asha", echo=echo)
    els = parse(doc, floor)
    rows = sum(e["kind"] == "row" for e in els)
    t.emit("parse", f"pages={len(doc['pages'])} elements={len(els)} table_rows={rows} "
           f"footers_dropped={sum(b['type'] == 'footer' for p in doc['pages'] for b in p['blocks'])}")
    ok, n = spotcheck(doc, els)
    t.emit("check", f"parse spotcheck={ok}/{n}", ok=ok, n=n)
    for e in els:
        if e.get("flagged"):
            t.emit("ocr", f"page={e['page']} conf={e['ocr_conf']:.2f} flagged "
                   f"(floor {floor:.2f})", page=e["page"])
    return {"trace": t, "elements": els, "chunks": chunks(doc, els), "spotcheck": (ok, n)}


def fixed_chunks(text, size=10):
    """The naive cut: every `size` words, wherever they fall (Vol 1 Chapter 14)."""
    w = text.split()
    return [" ".join(w[i:i + size]) for i in range(0, len(w), size)]


def cell_check(texts, header, row):
    """A row survives parsing if one chunk holds every cell next to its column name."""
    want = [f"{h}: {v}" for h, v in zip(header, row)]
    return any(all(w in t for w in want) for t in texts)
