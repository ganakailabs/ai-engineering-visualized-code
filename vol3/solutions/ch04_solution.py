"""Chapter 4 exercise: the rule that starts next month.

Add a clause that takes effect on 2026-11-01. On the pinned date (store.TODAY,
2026-10-04) the gate must exclude it; with the question dated 2026-11-02 it must be
used. Compare the effective date with the question's date, not the ingestion date.

Then add R6, which ended on 2026-09-30 (effective_to), and R7, whose effective_from is
not a date, and print the exact reason the gate gives for excluding each.
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

body += ("\n## R6 Summer returns\n"
         "tags: product=ALL region=ALL doc_type=policy effective_from=2026-06-01 "
         "effective_to=2026-09-30\n"
         "Summer orders can be returned within 45 days.\n"
         "\n## R7 Gift returns\n"
         "tags: product=ALL region=ALL doc_type=policy effective_from=2026-13-01\n"
         "Gifts can be returned for store credit.\n")
parents = C.section_chunks(meta, body)
for title in ("R6", "R7"):
    p, = [p for p in parents if p["title"].startswith(title)]
    ok, why = C.applies(p["tags"], "mug", "IN", TODAY)
    assert why == {"R6": "effective_to=2026-09-30 today=2026-10-04",
                   "R7": "effective_from='2026-13-01' is not a date"}[title], why
    print(f"{title} excluded: {why}")
print("ch04 solution: OK")
