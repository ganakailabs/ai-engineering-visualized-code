"""Implementation tests for Chapter 11: retrieval as a tool, judged by slots in code."""
import _path  # noqa: F401

import agentic_rag as rag
import ch11
from world import World

ASHA = ch11.ASHA

# MM-174: the sufficiency check on named slot cases
mugs = World().order("2001")
need = rag.slots(ch11.MUGS, ASHA)
assert need == ["order facts", "delivery date", "refund clause", "return shipping"]
filled, missing = rag.judge(need, {"R2": rag.HANDBOOK["R2"]}, None)
assert missing == ["order facts", "delivery date", "refund clause", "return shipping"]
filled, missing = rag.judge(need, {"R2": rag.HANDBOOK["R2"]}, mugs)
assert missing == ["return shipping"] and filled["refund clause"] == "R2"
filled, missing = rag.judge(need, {"R1": rag.HANDBOOK["R1"], "S3": rag.HANDBOOK["S3"]}, mugs)
assert missing == ["refund clause"], "R1 is the wrong clause for a damaged item"
assert "EU withdrawal" in rag.slots(ch11.MUGS, {"customer_id": "asha", "region": "EU"})

# labels: an IN customer never gets the EU-only passage
assert "S5" not in rag.search_knowledge("EU withdraw purchase", "IN")
assert "S5" in rag.search_knowledge("EU withdraw purchase", "EU")

# MM-173: the fixed pipeline leaves the second half uncovered; the agent fills it
f = rag.fixed(ch11.MUGS, ASHA, echo=False)
assert f["missing"] == ["return shipping"] and f["rounds"] == 1
a = rag.agentic(ch11.MUGS, ASHA, ch11.stub_agent, echo=False)
assert a["reason"] == "success" and a["cites"] == ["R2", "S3"] and a["rounds"] == 2
assert set(a["cites"]) <= set(a["evidence"])
assert a["store"].stop_record("T-11")["reason"] == "success"

# when the pipeline wins: one policy question, one round either way
g = rag.agentic(ch11.GIFT, ASHA, ch11.stub_agent, echo=False)
assert g["rounds"] == rag.fixed(ch11.GIFT, ASHA, echo=False)["rounds"] == 1
assert g["cites"] == ["S4"]

# BREAK/FIX strip "Search Forever"
broken = rag.agentic(ch11.PRICE, ASHA, ch11.search_forever(), extra_rounds=None,
                     gate=False, echo=False)                      # BREAK, documented
assert broken["rounds"] == 10 and "match any lower price" in broken["reply"]
assert broken["cites"] == [] and broken["missing"] == ["price match"]
fixed = rag.agentic(ch11.PRICE, ASHA, ch11.search_forever(), echo=False)   # FIX
assert fixed["rounds"] == 1 + rag.EXTRA_ROUNDS == 3
assert fixed["reason"] == "no_progress" and "match" not in fixed["reply"]
assert fixed["store"].stop_record("T-11")["reason"] == "no_progress"
assert fixed["store"].load("T-11")[0] == "HANDOFF"


# the budget holds whatever the model asks for, and an early "answer" is refused
def keeps_searching(user):
    return {"action": "search_knowledge", "query": "price match", "slot": "price match"}


def answers_early(user):
    return {"action": "answer", "text": "Yes, refund approved and shipping is free."}


r = rag.agentic(ch11.MUGS, ASHA, keeps_searching, echo=False)
assert r["rounds"] == 3 and r["reason"] == "no_progress"
r = rag.agentic(ch11.MUGS, ASHA, answers_early, echo=False)
assert r["rounds"] == 0 and r["reason"] != "success" and r["cites"] == []
assert "approved" not in r["reply"]

# a reply that is not a valid move ends with needs_human, not a guess
r = rag.agentic(ch11.MUGS, ASHA, lambda u: None, echo=False)
assert r["reason"] == "needs_human"

# another customer's order is not looked up
r = rag.agentic("Refund for #3100 please, it arrived broken", ASHA,
                lambda u: {"action": "look_up_order", "order_id": "3100"}, echo=False)
assert r["reason"] != "success" and "not found" in r["trace"].of("act")[0]["text"]
print("test_agentic_rag: OK")


# Real-model bug (llama3.2, Oct 24, 2026): every slot filled, but the model never chose
# "answer" and kept calling look_up_order until the step limit. FIX: code answers as soon
# as the check says enough.
def never_answers():
    moves = iter([{"action": "look_up_order", "order_id": "2001"},
                  {"action": "search_knowledge", "query": "refund damaged item",
                   "slot": "refund clause"},
                  {"action": "search_knowledge", "query": "return shipping for damaged items",
                   "slot": "return shipping"}])
    return lambda user: next(moves, {"action": "look_up_order", "order_id": "2001"})


r = rag.agentic(ch11.MUGS, ASHA, never_answers(), echo=False)
assert r["reason"] == "success", r["reason"]
assert r["rounds"] == 2 and set(r["cites"]) == {"R2", "S3"}, (r["rounds"], r["cites"])
assert len(r["trace"].of("act")) == 1, "no repeated lookups after the evidence sufficed"
print("test_agentic_rag: auto-answer OK")
