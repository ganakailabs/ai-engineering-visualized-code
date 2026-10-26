"""Implementation tests for Chapter 1: source contracts, routing and the decision check."""
import _path  # noqa: F401

import ch01
import sources as S
from world import World

ASHA = {"customer_id": "asha", "region": "IN"}

# MM-068: every source has a contract with the fields the router and checker read
assert set(S.CONTRACTS) == {"policy", "handbook", "manuals", "past_tickets", "orders", "stock"}
for c in S.CONTRACTS.values():
    for field in ("kind", "authority", "owner", "freshness", "scope", "answers", "decides"):
        assert field in c, (c["id"], field)
assert S.CONTRACTS["policy"]["version"] == "2026-09-15"
assert S.CONTRACTS["policy"]["tokens"] <= S.WHOLE_DOC_TOKENS < S.CONTRACTS["manuals"]["tokens"]

# MM-069: the access path comes from the contract, not from the question
assert S.path_for("orders") == "lookup" and S.path_for("stock") == "lookup"
assert S.path_for("policy") == "whole_doc"            # short, same for everyone
assert S.path_for("handbook") == "retrieve"           # per-passage region labels
assert S.path_for("manuals") == "retrieve"            # too long to read whole
assert S.path_for("past_tickets") == "retrieve"

# the stub classifier on the six chapter questions
expect = {ch01.Q[0]: ["order_fact"], ch01.Q[1]: ["how_to"], ch01.Q[2]: ["rule"],
          ch01.Q[3]: ["order_fact", "delivery"], ch01.Q[4]: ["history"],
          ch01.Q[5]: ["order_fact", "rule"]}
for q, needs in expect.items():
    assert S.needs(q) == needs, (q, S.needs(q))
    got, _ = S.classify(q)
    assert got == needs
assert S.route(["order_fact", "rule"]) == [("order_fact", "orders", "lookup"),
                                           ("rule", "policy", "whole_doc")]
assert S.route(["weather"]) == [("weather", None, "escalate")]
assert S.validate_needs({"needs": ["rule", "made_up"]}) is None   # unknown need: refuse
assert S.validate_needs("not json") is None

# fetch: lookup returns the live record with its version; scope is enforced
w = World()
ev = S.fetch("order_fact", "#2001", ASHA, w)
assert len(ev) == 1 and ev[0]["source"] == "orders" and ev[0]["path"] == "lookup"
assert ev[0]["fact"]["damaged"] is True and ev[0]["version"] == 1
assert S.fetch("order_fact", "#3100", ASHA, w) == []       # c-42's order: nothing comes back
pol = S.fetch("rule", "refund", ASHA, w)
assert [e["id"] for e in pol] == ["policy"] and pol[0]["version"] == "2026-09-15"
hb = S.fetch("region", "EU withdraw purchase", ASHA, w)
assert all(e["id"] != "S5" for e in hb), "an IN customer never gets the EU-only passage"
tickets = S.fetch("history", "NW-500 battery", ASHA, w)
assert all(e["customer"] == "asha" for e in tickets), "no other customer's ticket"

# Break/Fix: one retriever over everything, records included as text
naive = S.naive_retrieve(ch01.Q[5])
assert naive[0]["id"] == "PT-0004", naive
ok, why = S.check_decision([naive[0]], w)
assert not ok and any("cannot decide" in r for r in why), why
snap = dict(ev[0], path="retrieve")
ok, why = S.check_decision([snap], w)
assert not ok and any("snapshot" in r for r in why), why
w.orders["2001"]["version"] = 2                              # edited after the read
ok, why = S.check_decision(ev, w)
assert not ok and any("stale" in r for r in why), why
w = World()
ok, why = S.check_decision(S.fetch("order_fact", "#2001", ASHA, w) + pol, w)
assert ok and why == [], why

# end to end: the routed answer to the mug question cites the record and R2
r = ch01.answer(ch01.Q[5], ASHA, World(), echo=False)
assert r["decision"] == "refund or replace (R2)" and r["cites"] == ["order #2001", "R2"]
assert r["trace"].of("route")[0]["payload"]["paths"] == ["lookup", "whole_doc"]
assert r["trace"].of("check")[-1]["payload"]["ok"] is True
r = ch01.answer(ch01.Q[5], ASHA, World(), naive=True, echo=False)
assert r["decision"] is None and r["reason"] == "refused", r

# MM-086: counts come from records, not from retrieved text
rep = ch01.refund_window_report(ASHA, World())
assert rep["delivered"] == ["1234", "2001", "2077", "4410"]
assert rep["refundable"] == {"2001": "R2", "2077": "R2"}
assert rep["not_refundable"] == {"1234": "R1", "4410": "R3"}
print("test_sources: OK")
