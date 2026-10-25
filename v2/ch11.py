"""Chapter 11: Agentic RAG: Retrieval the Agent Chooses.

Run from the support-assistant folder:  python3 v2/ch11.py
Real model (optional):  AIEV_MODEL=ollama:llama3.2 python3 v2/ch11.py
The tickets are fixture data (fictional). The model chooses each step (search, look up
the order, or answer) and writes the queries; code checks the evidence and writes the
reply. The stub is a scripted agent (a demonstration, not a model).
"""
import re

import agentic_rag as rag
import llm

ASHA = {"customer_id": "asha", "region": "IN"}          # identity: the login session
MUGS = ("My mug set from #2001 arrived cracked. Can I get my money back, "
        "and who pays to send it back?")
GIFT = "Can I swap a gift card for cash?"
PRICE = "Do you price-match if I find it cheaper?"

SUB = {"refund clause": "refund damaged item", "return shipping":
       "return shipping for damaged items", "EU withdrawal": "EU withdraw purchase",
       "price match": "price match", "gift card": "gift card for cash"}


def stub_agent(user):
    """Scripted: search once, look up a named order, split per missing slot, answer."""
    missing = re.search(r"Missing slots: \[(.*)\]", user).group(1)
    missing = [m.strip(" '") for m in missing.split(",") if m.strip()]
    order = re.search(r"#(\d+)", user)
    unused = "unused" in user.split("\n")[0].lower()
    sub = dict(SUB, **({"refund clause": "unused item refund window",
                        "return shipping": "return shipping for unused items"}
                       if unused else {}))
    if '"passages": {}' in user and missing:
        slot = next((m for m in missing if m in sub), missing[0])
        return {"action": "search_knowledge", "query": sub.get(slot, slot), "slot": slot}
    if order and '"order": null' in user:
        return {"action": "look_up_order", "order_id": order.group(1)}
    slot = next((m for m in missing if m in sub), None)
    if slot:
        return {"action": "search_knowledge", "query": sub[slot], "slot": slot}
    return {"action": "answer"}


REWRITES = ["price match", "price-match policy", "match a lower price", "competitor price",
            "cheaper elsewhere", "price guarantee", "price adjustment",
            "lowest price promise", "beat a price", "price difference refund"]


def search_forever():
    """Scripted BREAK: rewrite the query each round; after ten searches, make one up."""
    tried = []

    def stub(user):
        if len(tried) < len(REWRITES):
            tried.append(REWRITES[len(tried)])
            return {"action": "search_knowledge", "query": tried[-1], "slot": "price match"}
        return {"action": "answer",
                "text": "Yes, we match any lower price within 14 days of purchase."}
    return stub


if __name__ == "__main__":
    print(f"model={llm.name()}")
    print("--- 1. Asha's two-part question, fixed pipeline vs agentic loop ---")
    rag.fixed(MUGS, ASHA)
    rag.agentic(MUGS, ASHA, stub_agent)
    print("--- 2. one well-formed policy question: the pipeline is enough ---")
    rag.fixed(GIFT, ASHA)
    rag.agentic(GIFT, ASHA, stub_agent)
    print("--- 3. BREAK: no budget, no gate (search forever) ---")
    rag.agentic(PRICE, ASHA, search_forever(), extra_rounds=None, gate=False)
    print("--- 4. FIX: two extra rounds, then stop with a reason ---")
    rag.agentic(PRICE, ASHA, search_forever())
