"""Knowledge graphs and multi-hop retrieval (Vol 3 Ch 13).

A small product-bundle-clause graph. Entities are resolved to one canonical name;
every edge cites the passage it came from. A coverage question returns one of three
answers: covered (an edge chain ends at a covering clause), excluded (an explicit
EXCLUDES edge or clause says no), or unknown (no edge). Unknown never means no: it
escalates. A relational join answers the same one-hop questions for comparison.
"""
import sqlite3

import _root  # noqa: F401

ALIASES = {  # surface name -> canonical entity
    "nw charger": "NW-500 charger", "nw-500 charger": "NW-500 charger",
    "usb-c charger (nw)": "NW-500 charger", "my headphones": "NW-500",
    "nw-500": "NW-500", "nw-500 case": "NW-500 case", "nw-500 ear tips": "NW-500 ear tips",
    "nw-500 cable": "NW-500 cable",
}

# (from, relation, to, source passage)
EDGES = [
    ("NW-500 charger", "PART_OF", "NW-500 Travel Bundle", "catalogue p.4 bundle contents"),
    ("NW-500 case", "PART_OF", "NW-500 Travel Bundle", "catalogue p.4 bundle contents"),
    ("NW-500 ear tips", "PART_OF", "NW-500 Travel Bundle", "catalogue p.4 bundle contents"),
    ("NW-500", "SOLD_WITH", "NW-500 Travel Bundle", "order 3100 line items"),
    ("NW-500 Travel Bundle", "COVERED_BY", "W2 bundle warranty", "policy W2@2026-09-15"),
    ("NW-500 ear tips", "EXCLUDES", "W2 bundle warranty", "policy W2.3 wear parts excluded"),
]


def resolve(name):
    return ALIASES.get(name.strip().lower(), name)


def out(node, rel=None):
    return [e for e in EDGES if e[0] == node and (rel is None or e[1] == rel)]


def coverage(part, warranty="W2 bundle warranty"):
    """Returns (verdict, hops). verdict in covered | excluded | unknown."""
    node = resolve(part)
    for e in out(node, "EXCLUDES"):
        if e[2] == warranty:
            return "excluded", [e]
    hops, frontier = [], node
    for _ in range(3):
        nxt = [e for e in out(frontier) if e[1] in ("PART_OF", "COVERED_BY")]
        if not nxt:
            return "unknown", hops
        hops.append(nxt[0])
        frontier = nxt[0][2]
        if frontier == warranty:
            return "covered", hops
    return "unknown", hops


def naive_coverage(part, warranty="W2 bundle warranty"):
    """The BREAK: no path is read as 'not covered'."""
    v, _ = coverage(part, warranty)
    return "not covered" if v == "unknown" else v


def join_db():
    c = sqlite3.connect(":memory:")
    c.execute("CREATE TABLE edges (src, rel, dst, source)")
    c.executemany("INSERT INTO edges VALUES (?,?,?,?)", EDGES)
    return c


def join_bundle(part):
    """One SQL join answers 'which warranty covers this part's bundle?' with no graph."""
    q = ("SELECT b.dst, a.source, b.source FROM edges a JOIN edges b ON a.dst = b.src "
         "WHERE a.src = ? AND a.rel = 'PART_OF' AND b.rel = 'COVERED_BY'")
    return join_db().execute(q, (resolve(part),)).fetchall()
