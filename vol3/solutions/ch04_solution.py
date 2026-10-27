"""Chapter 4 exercise: the rule that starts next month.

Add a clause that takes effect on 2026-11-01. On the pinned date (store.TODAY,
2026-10-04) the gate must exclude it; with the question dated 2026-11-02 it must be
used. Compare the effective date with the question's date, not the ingestion date.
"""
from datetime import date

import _path  # noqa: F401

import chunking as C
from store import TODAY

meta, body = C.read()
body += ("\n## R5 Store credit\n"
         "tags: product=ALL region=ALL doc_type=policy effective_from=2026-11-01\n"
         "Refunds can be taken as store credit with a 5 percent bonus.\n")
parents = C.section_chunks(meta, body)
r5 = [p for p in parents if p["title"].startswith("R5")]
assert len(r5) == 1

now = [p["id"] for p in C.gate(parents, "mug", "IN", TODAY)]
later = [p["id"] for p in C.gate(parents, "mug", "IN", date(2026, 11, 2))]
assert r5[0]["id"] not in now and r5[0]["id"] in later
print(f"today={TODAY}: R5 excluded; 2026-11-02: R5 used")
print("ch04 solution: OK")
