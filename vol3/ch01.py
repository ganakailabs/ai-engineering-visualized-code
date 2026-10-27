"""Chapter 1: The Knowledge Map: Source Contracts and Access Paths.

Run from the repo root:  python3 vol3/ch01.py
Real model (optional):  AIEV_MODEL=ollama:llama3.2 python3 vol3/ch01.py
The model names what each question needs; code reads the source contracts in
vol3/knowledge/sources.json, picks lookup, whole_doc or retrieve, fetches the evidence
and checks it before deciding. Questions, orders and tickets are fixture data
(fictional). The stub is a script (a demonstration, not a model).
"""
import _root  # noqa: F401

import llm
import sources as S
from events import Trace
from store import TODAY
from world import World

ASHA = {"customer_id": "asha", "region": "IN"}       # identity: the login session
Q = ["What did I pay for order #2001?",
     "How do I reset my NW-500 headphones?",
     "What is your refund policy?",
     "When will my order #6001 arrive?",
     "Has anyone else had NW-500 battery trouble before?",
     "Can I still return my mug set from #2001?"]


def refund_rule(o):
    """R1-R3 applied to one order record (code decides, not the model)."""
    days = (TODAY - o["delivered"]).days
    if o["final_sale"]:
        return False, "R3"
    if o["damaged"]:
        return days <= 7, "R2"
    return days <= 30, "R1"


def answer(question, customer, world, naive=False, echo=True):
    t = Trace(world, "T-ch01", customer["customer_id"], model=llm.name(), echo=echo)
    if naive:                                          # Break: retrieve everything as text
        ev = S.naive_retrieve(question)
        t.emit("retrieve", f"naive k=3 -> {', '.join(e['id'] for e in ev)}")
    else:
        need, _ = S.classify(question)
        if need is None:
            t.emit("escalate", "needs not understood -> human")
            return {"decision": None, "reason": "escalate", "cites": [], "trace": t}
        plan = S.route(need)
        t.emit("route", "  ".join(f"{n}->{c}:{p}" for n, c, p in plan),
               actor="model", needs=need, paths=[p for _, _, p in plan])
        ev = []
        for n, c, p in plan:
            got = S.fetch(n, question, customer, world)
            ev += got
            t.emit("retrieve", f"{p} {c} -> {', '.join(e['id'] for e in got) or 'nothing'}")
    ok, why = S.check_decision(ev, world)
    t.emit("check", "evidence -> ok" if ok else f"evidence -> refused: {why[0]}", ok=ok, why=why)
    order = next((e for e in ev if e["source"] == "orders"), None)
    if not ok or order is None or not any(e["source"] == "policy" for e in ev):
        return {"decision": None, "reason": "refused" if not ok else "no decision needed",
                "cites": [e["id"] for e in ev], "trace": t}
    yes, rule = refund_rule(order["fact"])
    decision = f"refund or replace ({rule})" if yes and rule == "R2" else \
        (f"refund ({rule})" if yes else f"no refund ({rule})")
    t.emit("decide", f"{order['id']} -> {decision}", rule=rule)
    return {"decision": decision, "reason": "success", "cites": [order["id"], rule], "trace": t}


# MM-086: counts and filters come from records; text explains them
def refund_window_report(customer, world):
    mine = {oid: o for oid, o in world.orders.items() if o["owner"] == customer["customer_id"]}
    delivered = sorted(oid for oid, o in mine.items() if o["delivered"])
    yes, no = {}, {}
    for oid in delivered:
        ok, rule = refund_rule(mine[oid])
        (yes if ok else no)[oid] = rule
    return {"delivered": delivered, "refundable": yes, "not_refundable": no}


if __name__ == "__main__":
    print("Part 1 (MM-068): the source contracts")
    for cid, c in S.CONTRACTS.items():
        dec = "decides" if c["decides"] else "-"
        print(f"  {cid:<13}{c['kind']:<9}{c['authority']:<14}{dec:<8}path={S.path_for(cid)}"
              + (f" tokens={c['tokens']}" if "tokens" in c else ""))
    print("\nPart 2 (MM-069): route six questions")
    for q in Q:
        need, _ = S.classify(q)
        plan = S.route(need) if need else [("?", None, "escalate")]
        print(f"  {q}\n    -> " + "  ".join(f"{c}:{p}" for _, c, p in plan))
    print(f"\nPart 3 (Break/Fix): {Q[5]}")
    print("BREAK (one retriever over everything):")
    r = answer(Q[5], ASHA, World(), naive=True)
    print(f"  decision={r['decision']} stop={r['reason']}")
    print("FIX (routed by contract):")
    r = answer(Q[5], ASHA, World())
    print(f"  decision={r['decision']} cites={r['cites']}")
    print("\nPart 4 (MM-086): which of my delivered orders can still be refunded?")
    rep = refund_window_report(ASHA, World())
    print(f"  delivered={len(rep['delivered'])} refundable={rep['refundable']}\n"
          f"    not_refundable={rep['not_refundable']}")
    naive = S.naive_retrieve("which of my orders can be refunded")
    print(f"  retrieved as text, k=3: {[e['id'] for e in naive]}\n"
          "    (no count can come from this)")
