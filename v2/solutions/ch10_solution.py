"""Chapter 10 exercise: halve the budget.

Run the 30-step dispute ticket at half the budget. Compaction happens earlier and more
often; every pin and the open UNKNOWN refund must still be in every model call, because
they are projected from state, not kept by the summary.
"""
from _path import STUB

import ch10

r = ch10.run(pinned=True, budget=ch10.BUDGET // 2)
compactions = len(r["trace"].of("compact"))
assert compactions >= 1
for s in r["log"]:
    assert s["pins"] == s["need_pins"] == 3, s
    assert s["owed"] == s["need_owed"] == 1, s
    assert s["tokens"] <= ch10.BUDGET // 2, s
assert r["book"].row(ch10.OP)["state"] == "UNKNOWN"
assert len(r["world"].payments) == 1
if STUB:
    assert r["move"] == {"action": "reconcile", "order_id": "2001"}
print(f"budget={ch10.BUDGET // 2} compactions={compactions} "
      f"pins and obligations kept on all {len(r['log'])} steps")
print("ch10 solution: OK")
