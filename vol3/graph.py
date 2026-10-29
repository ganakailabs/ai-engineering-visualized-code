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


def out(node, rel=None, edges=None):
    return [e for e in (EDGES if edges is None else edges)
            if e[0] == node and (rel is None or e[1] == rel)]


MAX_HOPS = 3


def coverage(part, warranty="W2 bundle warranty", edges=None, max_hops=MAX_HOPS):
    """Returns (verdict, hops). verdict in covered | excluded | unknown.

    Breadth-first over PART_OF and COVERED_BY edges, at most max_hops deep, with a
    visited set so a cycle cannot loop. Every branch is explored, so a dead-end edge
    listed first cannot hide a covering path, and the answer does not depend on edge
    order (neighbours are visited in sorted order; the shortest path wins).
    An explicit EXCLUDES edge from the part wins over any covering path."""
    node = resolve(part)
    for e in out(node, "EXCLUDES", edges):
        if e[2] == warranty:
            return "excluded", [e]
    frontier, seen = [(node, [])], {node}
    for _ in range(max_hops):
        nxt = []
        for here, path in frontier:
            for e in sorted(x for x in out(here, edges=edges) if x[1] in ("PART_OF", "COVERED_BY")):
                if e[2] == warranty:
                    return "covered", path + [e]
                if e[2] not in seen:
                    seen.add(e[2])
                    nxt.append((e[2], path + [e]))
        if not nxt:
            break
        frontier = nxt
    return "unknown", []


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
