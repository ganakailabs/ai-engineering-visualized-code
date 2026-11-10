"""Tests for cost.py (Chapter 9)."""
import _path  # noqa: F401

import cost as C
from ch09 import T1, T2

big, small = C.tickets("big"), C.tickets("small")
assert C.per_call(small) < C.per_call(big)          # cheaper calls...
assert C.per_resolved(small) > C.per_resolved(big)  # ...dearer resolved tickets
assert C.tickets("big") == big                      # seeded: same week every run

q1 = "Can I get a refund for order #2001? It arrived cracked."
q2 = "Can I get a refund for order #3100? It arrived cracked."
naive = C.AppCache("p1", "i1", entity=False, structured=False)
naive.put(q1, "r2001")
assert naive.get(q2)[0] == "r2001"                  # the wrong-order bug, reproduced
ent = C.AppCache("p1", "i1", structured=False)
ent.put(q1, "r2001")
assert ent.get(q2) == (None, "semantic miss reason=order id differs")
PERSONAL_CTX = dict(C.GENERAL, route="refund", context=True, sources=["order"])
assert C.AppCache("p1", "i1").put(q1, "x", PERSONAL_CTX).startswith("not cached")
# context-only personal request: the text rule misses it, structured cacheability does not
vague = "Please refund the order we discussed."
assert C.text_rule(vague) is False
assert C.AppCache("p1", "i1").put(vague, "x", PERSONAL_CTX).startswith("not cached")
assert C.AppCache("p1", "i1").put("What is R3?", "x",
                                   dict(C.GENERAL, sources=["handbook", "order"])
                                   ).startswith("not cached")
# scope and recheck: another tenant, new permissions, revoked access never reuse a hit
sc = C.AppCache("p1", "i1")
sc.put("How long does delivery take?", "faq")
assert sc.get("How long does delivery take?", dict(C.GENERAL, tenant="b"))[0] is None
assert sc.get("How long does delivery take?", dict(C.GENERAL, perm_v=2))[0] is None
assert sc.get("how long does delivery take", dict(C.GENERAL, can_read=set())) == \
    (None, "hit refused reason=access")
assert sc.get("How long does delivery usually take?", dict(C.GENERAL, can_read=set()))[0] is None
c = C.AppCache("p1", "i1")
c.put("How long does delivery take?", "faq")
assert c.get("how long does delivery take")[1] == "exact hit"
assert c.set_versions("p2", "i1") == 1 and c.get("How long does delivery take?")[0] is None

assert not C.prefix_stable(T1, T2, C.AS_SHIPPED)
assert C.prefix_stable(T1, T2, C.STABLE_FIRST)
print("test_cost: OK")
