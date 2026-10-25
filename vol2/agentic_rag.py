"""Chapter 11: agentic RAG, retrieval the agent chooses.

MM-173 Retrieval Is a Tool: search_knowledge is one tool among others. The model decides
       whether to call it, with which query, or to look up the order instead. Vol 1's
       fixed pipeline (ch15.py) retrieves once, the same way, for every question.
MM-174 Is the Evidence Enough?: a sufficiency check IN CODE compares the evidence with
       the slots the decision needs and names what is missing. The agent answers only
       when every slot is filled; otherwise it re-queries or splits the question, within
       a budget of 2 extra retrieval rounds (D2-11), then stops with a reason (MM-172).

search_knowledge wraps Vol 1's index: ch13.hybrid (keyword + meaning, fused, with the
"nothing close enough" floors) over passages filtered by their region label (ch14). The
reply is written by code from the slots, so it can only cite passages that came back.
The slot rules and the question router are toys for the fixture handbook.
"""
import json
import re

import _root  # noqa: F401  (Vol 1 ch13.py, ch15.py, store.py)

import llm
import state
from ch13 import hybrid
from ch15 import index, retrieve
from events import Trace
from store import HANDBOOK, REGION, TODAY
from world import OWNERS, World

EXTRA_ROUNDS = 2                     # D2-11: two retrieval rounds after the first
MAX_STEPS = 8                        # all tool calls, retrieval or not


def search_knowledge(query, region="ALL", k=3):
    """The tool: top-k handbook passages for this customer's region, maybe none."""
    allowed = {cid: t for cid, t in HANDBOOK.items() if REGION[cid] in ("ALL", region)}
    return {cid: allowed[cid] for cid in hybrid(query, docs=allowed, k=k)}


# ---- what each part of a question needs (toy router over the fixture tickets) ----
def parts(question):
    q = question.lower()
    out = []
    if "gift card" in q:
        return ["gift_card"]
    if any(w in q for w in ("money back", "refund", "return the")):
        out.append("refund")
    if any(w in q for w in ("send it back", "shipping")):
        out.append("return_shipping")
    if "price" in q and "match" in q:
        out.append("price_match")
    return out


def slots(question, session):
    need = []
    for part in parts(question):
        if part == "refund":
            need += ["order facts", "delivery date", "refund clause"]
            if session.get("region") == "EU":
                need.append("EU withdrawal")
        elif part == "return_shipping":
            need.append("return shipping")
        elif part == "gift_card":
            need.append("gift card")
        elif part == "price_match":
            need.append("price match")
    return need


def clause_for(order):
    if order["final_sale"]:
        return "Final-sale"
    return "Damaged items" if order["damaged"] else "Unused items"


def judge(need, evidence, order):
    """MM-174: which slots are filled, and by which retrieved passage. Code, not a model."""
    filled = {}
    for slot in need:
        if slot in ("order facts", "delivery date"):
            if order and (slot == "order facts" or order.get("delivered")):
                filled[slot] = f"order {order['order_id']}"
            continue
        want = {"refund clause": clause_for(order) if order else None,
                "EU withdrawal": "withdraw", "return shipping": "return shipping",
                "price match": "price match", "gift card": "gift card"}[slot]
        hit = [cid for cid, t in evidence.items() if want and want.lower() in t.lower()
               and (slot != "refund clause" or "refund" in t.lower())]
        if hit:
            filled[slot] = hit[0]
    return filled, [s for s in need if s not in filled]


def compose(need, filled, order):
    """The reply, built only from filled slots: every citation is a retrieved id."""
    days = (TODAY - order["delivered"]).days if order else None
    lines, cites = [], []
    if "refund clause" in filled:
        r = filled["refund clause"]
        window = {"Damaged items": 7, "Unused items": 30}.get(clause_for(order), 0)
        ok = days is not None and days <= window
        cites.append(r)
        if "EU withdrawal" in filled:
            cites.append(filled["EU withdrawal"])
            ok = ok or days <= 14
        lines.append(f"refund {'approved' if ok else 'declined'}: delivered {days} days ago"
                     + (" (photo needed)" if order["damaged"] else ""))
    if "gift card" in filled:
        cites.append(filled["gift card"])
        lines.append("gift card cannot be exchanged for cash")
    if "return shipping" in filled:
        cites.append(filled["return shipping"])
        lines.append("return shipping " + ("free (damaged)" if order and order["damaged"]
                                          else "paid by the customer"))
    return "; ".join(lines), cites


DECIDE_SYSTEM = (
    "You are the Northwind Goods support agent. Choose ONE next step. Reply with ONE "
    'JSON object and nothing else: {"action": "search_knowledge", "query": "<short '
    'search query>", "slot": "<missing slot it is for>"} or {"action": "look_up_order", '
    '"order_id": "<id>"} or {"action": "answer"}. Look up the order the customer names. '
    "Search the handbook for each missing slot. Answer when nothing is missing.")


def ask(question, known, missing, rounds_left, stub):
    user = (f"Customer: {question}\nKnown: {json.dumps(known, default=str)}\n"
            f"Missing slots: {missing}\nSearch rounds left: {rounds_left}")
    move, _ = llm.ask_json(DECIDE_SYSTEM, user, stub, max_output_tokens=120)
    return move


def agentic(question, session, stub, extra_rounds=EXTRA_ROUNDS, gate=True, echo=True,
            ticket="T-11"):
    """One ticket through the agentic loop. extra_rounds=None, gate=False is the BREAK."""
    world = World()
    tr = Trace(world, ticket, session["customer_id"], model=llm.name(), echo=echo)
    store = state.Store()
    store.create(ticket, {"question": question})
    store.move(ticket, "ACTING", store.move(ticket, "VERIFYING", 1))
    need, evidence, order, searched, rounds = slots(question, session), {}, None, set(), 0
    cap = 1 + extra_rounds if extra_rounds is not None else 10    # BREAK: demo cap only
    missing, filled, reason, reply, cites = list(need), {}, None, "", []
    for _ in range(MAX_STEPS if gate else 20):
        known = {"order": order, "passages": evidence}
        move = ask(question, known, missing, cap - rounds, stub)
        act = (move or {}).get("action")
        if act == "search_knowledge" and rounds < cap:
            query, slot = str(move.get("query", question)), move.get("slot") or (missing or ["?"])[0]
            label = ("decide" if rounds == 0 else "requery" if slot in searched
                     else "decompose")
            tr.emit(label, (f'retrieve source=handbook query="{query}"' if label == "decide"
                            else f'sub="{query}" for={slot}' if label == "decompose"
                            else f'query="{query}" for={slot} round={rounds + 1}/{cap}'),
                    actor="model")
            hits = search_knowledge(query, session.get("region", "ALL"))
            rounds += 1
            searched.add(slot)
            evidence.update(hits)
            tr.emit("retrieve", f"ids={list(hits)} round={rounds}")
        elif act == "look_up_order":
            oid = str(move.get("order_id", "")).lstrip("#")
            o = world.order(oid) if OWNERS.get(oid) == session["customer_id"] else None
            order = o or order
            tr.emit("act", f"look_up_order {oid} -> " + (
                f"delivered {o['delivered']} damaged={'yes' if o['damaged'] else 'no'}"
                if o else "not found for this customer"))
        elif act == "answer" and not gate:                    # BREAK: the model's word
            reply = str(move.get("text", "")) or "answer with no evidence"
            reason = "success"
            break
        elif act == "answer" and not missing:
            reply, cites = compose(need, filled, order)
            reason = "success"
            break
        elif act == "search_knowledge" or (act == "answer" and rounds >= cap):
            reason = "no_progress"                            # budget spent, slots open
            break
        elif act != "answer":
            reason = "needs_human"                            # not a valid move
            break
        filled, missing = judge(need, evidence, order)
        if gate:
            tr.emit("judge", f"sufficient={'yes -> answer' if not missing else 'no'}"
                    + (f" missing=[{', '.join(missing)}]" if missing else ""))
            if not missing:                                   # FIX: enough means answer now
                reply, cites = compose(need, filled, order)
                reason = "success"
                break
    else:
        reason = "budget_exhausted"
    store.stop(ticket, reason, f"rounds={rounds}/{cap}"
               + (f" missing=[{', '.join(missing)}]" if missing and gate else ""))
    tr.emit("stop", f"reason={reason} rounds={rounds}/{cap}"
            + (" -> handoff" if state.STOPS[reason][0] == "HANDOFF" else ""), reason=reason)
    if reason != "success":
        reply = state.STOPS[reason][1]
    tr.emit("reply", (f"cites=[{', '.join(cites)}] " if cites else "") + reply)
    return {"reason": reason, "rounds": rounds, "cites": cites, "reply": reply,
            "evidence": evidence, "missing": missing, "trace": tr, "store": store,
            "need": need}


def fixed(question, session, echo=True):
    """Vol 1's pipeline (ch15): retrieve once, top 3, then answer. Judged after the fact,
    with the order facts handed over for free, so only the handbook gap shows."""
    ids = list(retrieve(question, index()))
    oid = next(iter(re.findall(r"#(\d+)", question)), None)
    order = World().order(oid) if oid else None
    _, missing = judge(slots(question, session), {c: HANDBOOK[c] for c in ids}, order)
    if echo:
        print(f"  fixed    retrieve top=3 ids={ids} -> answer (one round)"
              f"; not covered: [{', '.join(missing) or 'none'}]")
    return {"ids": ids, "missing": missing, "rounds": 1}
