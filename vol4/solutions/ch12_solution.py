"""Chapter 12 exercise: Starve the gate.

Remove 80 percent of the labelled training tickets, then run the gates. Predict first:
which gate closes? The TRY gate, on its LABELLED DATA lock: 20 percent of 648 is 129
tickets, under the 500 the gate asks for. Nothing is trained, so there is no student
to bring to the SHIP gate. Tickets are the chapter's simulated set.
"""
import _path  # noqa: F401

import random

import triage as T

tr, va, te = T.split(T.dedup(T.make_tickets()))
kept = random.Random(1).sample(tr, len(tr) // 5)
opened, why = T.gate_try(plateau=True, labelled=len(kept))
print(f"labelled kept={len(kept)} of {len(tr)}")
print(f"gate try plateau=yes labelled={len(kept)} -> "
      f"{'open' if opened else 'closed'} {' '.join(why)}")
student = T.NaiveBayes().fit([t["text"] for t in kept],
                             [t["human"] for t in kept]) if opened else None
print(f"trained: {'yes' if student else 'no'}")
assert not opened and why == [f"labelled={len(kept)}<500"]
assert student is None
print("ch12 solution: OK")
