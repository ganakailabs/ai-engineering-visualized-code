"""Chapter 1 exercise: route the stock question and a mixed question.

1. "Is the green mug set in stock?" must go to the stock record by lookup.
2. "How many of my delivered orders are final sale, and why can't they be refunded?"
   needs a count from the order records (lookup) and the reason from the policy
   (whole_doc). The stub's keywords miss "my delivered orders"; widen the order_fact
   pattern so it matches.
"""
from _path import STUB

import ch01
import sources as S
from world import World

S.KEYWORDS[0] = ("order_fact", r"#\d+|\bmy (\w+ )?orders?\b")     # the fix
STOCK_Q = "Is the green mug set in stock?"
MIXED_Q = "How many of my delivered orders are final sale, and why can't they be refunded?"
w = World()

need, _ = S.classify(STOCK_Q)
assert need and "stock" in need, need
(_, cid, path), = [r for r in S.route(need) if r[0] == "stock"]
assert (cid, path) == ("stock", "lookup")
ev = S.fetch("stock", STOCK_Q, ch01.ASHA, w)
assert ev[0]["fact"] == {"item": "mug set green", "count": 4}

need, _ = S.classify(MIXED_Q)
assert need and {"order_fact", "rule"} <= set(need), need
if STUB:
    assert S.route(need) == [("order_fact", "orders", "lookup"), ("rule", "policy", "whole_doc")]
rep = ch01.refund_window_report(ch01.ASHA, w)
final = [oid for oid in rep["delivered"] if w.orders[oid]["final_sale"]]   # count from records
assert final == ["4410"] and rep["not_refundable"]["4410"] == "R3"
reason = S.fetch("rule", MIXED_Q, ch01.ASHA, w)[0]
assert "[R3] Final-sale items cannot be refunded." in reason["text"]
ok, why = S.check_decision(S.fetch("order_fact", "#4410", ch01.ASHA, w) + [reason], w)
assert ok, why
print(f"stock: lookup -> {ev[0]['fact']['count']} green mug sets")
print(f"final sale: {len(final)} order (#{final[0]}), reason R3 from policy {reason['version']}")
print("ch01 solution: OK")
