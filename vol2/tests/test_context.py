"""Implementation tests for Chapter 10: pins and obligations survive every compaction."""
import _path  # noqa: F401

import ch10
import context

# BREAK/FIX strip "Compaction Dropped the Key Fact"
broken = ch10.run(pinned=False, echo=False)                       # BREAK, documented
after = [s for s in broken["log"] if s["step"] >= 24]
assert after and all(s["owed"] == 0 for s in after), "the summary lost the UNKNOWN row"
assert "2001" not in broken["ctx"].summary and "UNKNOWN" not in broken["ctx"].summary

fixed = ch10.run(pinned=True, echo=False)                         # FIX
assert fixed["ctx"].summary, "compaction happened"
for s in fixed["log"]:                                            # every step, every call
    assert s["pins"] == s["need_pins"] == 3 and s["owed"] == s["need_owed"] == 1, s
    assert s["tokens"] <= ch10.BUDGET, s

# identity comes from the session, even though the summary never names the customer
assert "asha" not in fixed["ctx"].summary
pins, owed = context.project(fixed["session"], fixed["store"], fixed["book"], ch10.TICKET,
                             [ch10.OP])
assert pins["customer"] == "asha" and pins["order"] == "2001"
assert fixed["book"].row(ch10.OP)["state"] == "UNKNOWN" and len(owed) == 1

# just in time: only R2 is loaded, and only at the last step
assert list(fixed["ctx"].loaded) == ["R2"]
assert context.up_front_tokens() > context.count(fixed["ctx"].loaded["R2"])

# the ledger still guards the write: a refund chosen from a lossy context does not pay twice
row = broken["book"].execute(ch10.OP, ch10.ARGS, ch10.pay(broken["world"]),
                             ch10.find(broken["world"]))
assert row["state"] == "CONFIRMED" and len(broken["world"].payments) == 1

# a reconciled row is no longer an obligation
pins, owed = context.project(broken["session"], broken["store"], broken["book"],
                             ch10.TICKET, [ch10.OP])
assert owed == []
# a summarizer that writes too much cannot push the call over budget (found on llama3.2)
c = context.Context(60, lambda prev, turns: "word " * 80)
for i in range(12):
    c.add(f"step {i} customer: still waiting for my refund on the mug set")
    text, tokens, _ = c.fit("PINNED: - customer: asha")
    assert tokens <= 60 and "customer: asha" in text, (i, tokens)
print("test_context: OK")
