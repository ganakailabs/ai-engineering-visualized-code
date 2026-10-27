"""Source contracts, the router and the decision check (Vol 3 Chapter 1).

Every source the assistant reads has a contract in knowledge/sources.json: who owns
it, how fresh it is, who may see it, which questions it answers and whether a decision
may rest on it. The model names what a question needs; code picks the source and the
access path from the contract, fetches the evidence and checks it before it decides.
"""
import json
import re
from pathlib import Path

import _root  # noqa: F401  (Vol 2 and Vol 1 on the path)

import events
import llm
import store
from ch13 import keyword_score
from stub_model import rough_token_count

KNOWLEDGE = Path(__file__).resolve().parent / "knowledge"
WHOLE_DOC_TOKENS = 200   # PLACEHOLDER: the slice of the context this book reserves for
                         # one whole document; measure your own model's budget
NEEDS = ("order_fact", "stock", "rule", "delivery", "warranty", "region", "how_to", "history")


def _manual_blocks():
    """Each manual block as a passage. Chapter 2 builds the real ingestion."""
    out = {}
    for f in sorted((KNOWLEDGE / "manuals").glob("*.txt")):
        head, _, body = f.read_text().partition("=== page 1 ===")
        src = re.search(r"source: (\S+)", head).group(1)
        for p, page in enumerate(("=== page 1 ===" + body).split("=== page ")[1:], 1):
            blocks = [b.strip() for b in page.split("\n", 1)[1].split("\n\n") if b.strip()]
            for b, text in enumerate(blocks, 1):
                out[f"{src}:p{p}.b{b}"] = text
    return out


TICKETS = json.loads((KNOWLEDGE / "past_tickets.json").read_text())["tickets"]
TEXT = {"policy": {"policy": store.policy_text()},
        "handbook": {c: t for c, t in store.HANDBOOK.items() if c.startswith("S")},
        "manuals": _manual_blocks(),
        "past_tickets": {t["id"]: t["text"] for t in TICKETS}}


def _load():
    contracts = {c["id"]: c for c in
                 json.loads((KNOWLEDGE / "sources.json").read_text())["sources"]}
    for cid, c in contracts.items():
        if c["kind"] == "document":
            c["tokens"] = rough_token_count(" ".join(TEXT[cid].values()))
        c["version"] = store.POLICY_VERSION if cid in ("policy", "handbook") else "live"
    return contracts


CONTRACTS = _load()
events.KINDS.update({"load", "ingest", "rerun", "index"})  # Vol 3 (series contract section 4)


# MM-069: the path comes from the contract
def path_for(cid):
    c = CONTRACTS[cid]
    if c["kind"] == "record":
        return "lookup"                  # exact facts: ask the owner
    if c["uniform_scope"] and c["tokens"] <= WHOLE_DOC_TOKENS:
        return "whole_doc"               # short, same for all: read it
    return "retrieve"                    # long or per reader: search


KEYWORDS = [("order_fact", r"#\d+|\bmy order\b"), ("stock", r"\bin stock\b|\bavailable\b"),
            ("rule", r"\brefund|\breturn\b|money back|\bpolicy\b"),
            ("delivery", r"\barrive|\bdelivery\b|\btrack"), ("warranty", r"\bwarranty|\bdefect"),
            ("region", r"\bEU\b|\bwithdraw"), ("how_to", r"\bhow do i\b|\breset\b|\bclean\b"),
            ("history", r"\banyone\b|\bbefore\b")]


def needs(question):
    """The stub's answer (a script, not a model): what the question needs."""
    return [n for n, pat in KEYWORDS if re.search(pat, question, re.I)]


def validate_needs(reply):
    if not isinstance(reply, dict) or not isinstance(reply.get("needs"), list):
        return None
    got = reply["needs"]
    return got if got and all(n in NEEDS for n in got) else None


SYSTEM = ("You classify a Northwind Goods support question. Reply with JSON "
          '{"needs": [...]} using only these names: ' + ", ".join(NEEDS) + ".")


def classify(question):
    """The model names the needs; code validates them. None -> escalate."""
    reply, raw = llm.ask_json(SYSTEM, question, lambda q: {"needs": needs(q)})
    return validate_needs(reply), raw


def route(need_list):
    out = []
    for n in need_list:
        cid = next((c for c, k in CONTRACTS.items() if n in k["answers"]), None)
        out.append((n, cid, path_for(cid) if cid else "escalate"))
    return out


def _ev(source, path, eid, version, text, **extra):
    return dict({"source": source, "path": path, "id": eid, "version": version,
                 "text": text}, **extra)


def fetch(need, query, customer, world, k=2):
    """Evidence for one need, by the path the contract sets, inside the contract's scope."""
    (_, cid, path), = route([need])
    if cid == "orders":
        m = re.search(r"#?(\d{4})", query)
        o = world.orders.get(m.group(1)) if m else None
        if not o or o["owner"] != customer["customer_id"]:
            return []                                  # scope: the owner only
        return [_ev("orders", path, f"order #{m.group(1)}", o["version"],
                    f"order #{m.group(1)}: {o['item']}", fact=dict(o))]
    if cid == "stock":
        item = next((s for s in world.stock                  # every word of the item name
                     if all(w in query.lower().split() for w in s.split())), None)
        return [_ev("stock", path, item, "live", f"{item}: {world.stock[item]}",
                    fact={"item": item, "count": world.stock[item]})] if item else []
    if path == "whole_doc":
        return [_ev(cid, path, cid, CONTRACTS[cid]["version"], TEXT[cid][cid])]
    docs = dict(TEXT[cid])
    if cid == "handbook":                              # scope: region labels
        docs = {i: t for i, t in docs.items()
                if store.REGION[i] in ("ALL", customer["region"])}
    if cid == "past_tickets":                          # scope: this customer only
        docs = {t["id"]: t["text"] for t in TICKETS if t["customer"] == customer["customer_id"]}
    ranked = sorted(((keyword_score(query, t), i) for i, t in docs.items()), reverse=True)
    out = []
    for s, i in ranked[:k]:
        if s > 0:
            extra = {"customer": customer["customer_id"]} if cid == "past_tickets" else {}
            out.append(_ev(cid, path, i, CONTRACTS[cid]["version"], docs[i], **extra))
    return out


def naive_retrieve(question, k=3):
    """The Break: one retriever over every source, order snapshots included as text."""
    docs = [(cid, i, t) for cid, d in TEXT.items() for i, t in d.items()]
    ranked = sorted(docs, key=lambda d: -keyword_score(question, d[2]))
    return [_ev(cid, "retrieve", i, CONTRACTS[cid]["version"], t) for cid, i, t in ranked[:k]]


def check_decision(evidence, world):
    """A decision may rest only on sources that decide, read by their contract path,
    at the version that is current now. Returns (ok, reasons)."""
    why = []
    for e in evidence:
        c = CONTRACTS[e["source"]]
        if not c["decides"]:
            why.append(f"{e['id']}: {c['authority']}, cannot decide")
            continue
        if e["path"] != path_for(e["source"]):
            why.append(f"{e['id']} read by {e['path']}: a snapshot, not the {path_for(e['source'])}")
            continue
        if e["source"] == "orders":
            now = world.orders[e["id"].split("#")[1]]["version"]
            if e["version"] != now:
                why.append(f"{e['id']} version {e['version']} is stale (now {now})")
        elif e["version"] != c["version"]:
            why.append(f"{e['id']} version {e['version']} is stale (now {c['version']})")
    return not why, why
