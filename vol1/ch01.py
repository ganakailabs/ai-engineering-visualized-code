"""Chapter 1: AI Engineering Is a System."""
import re
import time

from stub_model import call_model
from store import STORE_NAME, TODAY, fetch_order, policy_text


# --- v0: the demo (one arrow) -------------------------------------------
def handle_v0(message: str) -> str:
    messages = [
        {"role": "system", "content": "You are a helpful support agent. Answer the customer."},
        {"role": "user", "content": message},
    ]
    return call_model(messages)["text"]


# --- v1: the system (every box) -----------------------------------------
def fetch_context(message):
    m = re.search(r"#?(\d{4})", message)
    order_id = m.group(1) if m else None
    return order_id, fetch_order(order_id)


def build_prompt(message, order_id, order):
    facts = (f"order_id={order_id} item={order['item']} amount={order['amount']} "
             f"days_since_delivery={(TODAY - order['delivered']).days} "
             f"final_sale={str(order['final_sale']).lower()}")
    system = (f"You decide refund requests for {STORE_NAME}, an online store. Use ONLY the policy "
              "and order facts below. Reply as '<approve|deny|escalate>: <reason with clause id>'.\n"
              + policy_text() + "\nORDER FACTS: " + facts)
    return [{"role": "system", "content": system},
            {"role": "user", "content": message}]


def check_decision(text, order):
    decision = text.split(":", 1)[0].strip().lower()
    days = (TODAY - order["delivered"]).days
    allowed = (not order["final_sale"] and days <= 30
               and order["amount"] <= 5000)
    if decision not in ("approve", "deny", "escalate"):
        return "escalate", "unparseable model output"
    if decision == "approve" and not allowed:
        return ("escalate",
                "model approved a refund the rules do not allow")
    return decision, "ok"


def handle_v1(message):
    trace = {"message": message, "stops": []}

    def stop(name, start, **data):
        trace["stops"].append({"stop": name, "ms": round((time.perf_counter() - start) * 1000, 2), **data})

    t = time.perf_counter()
    order_id, order = fetch_context(message)
    stop("fetch_context", t, order_id=order_id, found=order is not None)
    if order is None:  # fail loudly instead of letting the model guess
        trace["reply"] = "Could you share your order number? I could not find it."
        return trace

    t = time.perf_counter()
    messages = build_prompt(message, order_id, order)
    stop("build_prompt", t, chars=sum(len(m["content"]) for m in messages))

    t = time.perf_counter()
    result = call_model(messages)
    stop("call_model", t, output=result["text"], usage=result["usage"])

    t = time.perf_counter()
    decision, reason = check_decision(result["text"], order)
    stop("check_decision", t, decision=decision, reason=reason)

    trace["reply"] = {"approve": "Your refund is approved.",
                      "deny": "Sorry, this order is not eligible: " + result["text"].split(":", 1)[-1].strip(),
                      "escalate": "I have passed this to a human agent."}[decision]
    return trace  # step 6: respond and log (here: return the trace)


if __name__ == "__main__":
    ticket = "Can I get a refund for order #1234?"
    print("v0:", handle_v0(ticket))
    tr = handle_v1(ticket)
    print("v1:", tr["reply"])
    for s in tr["stops"]:
        print("  ", s["stop"], {k: v for k, v in s.items() if k not in ("stop", "ms")})
    print("no order number:", handle_v1("Can I get a refund? It broke.")["reply"])
