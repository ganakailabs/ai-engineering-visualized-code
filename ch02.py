"""Chapter 2: What an LLM Is."""
from stub_model import call_model
from store import TODAY, fetch_order, policy_text
from ch01 import handle_v1, check_decision

VALID = ("approve", "deny", "escalate")


# MM-003: an assistant follows instructions, so the format is yours to state
def format_ok(text: str) -> bool:
    return text.split(":", 1)[0].strip().lower() in VALID


# MM-004: the model cannot know your orders or today's date
def ask_status_v0(message):
    return call_model([{"role": "user", "content": message}])["text"]


def ask_status_v1(order_id):
    order = fetch_order(order_id)  # a lookup answers a status question
    return f"Order {order_id} ({order['item']}) was delivered on {order['delivered']}."


# MM-005: decide in code, let the model write the words
def decide(order) -> str:
    days = (TODAY - order["delivered"]).days
    if order["final_sale"] or days > 30:
        return "deny"
    if order["amount"] > 5000:
        return "escalate"
    return "approve"


def order_facts(order_id, order) -> str:
    days = (TODAY - order["delivered"]).days
    return (f"\nORDER FACTS: order_id={order_id} amount={order['amount']} "
            f"days_since_delivery={days} final_sale={str(order['final_sale']).lower()}")


def handle_v2(message, order_id):
    order = fetch_order(order_id)
    decision = decide(order)  # rules hold regardless of tone
    system = (f"DECISION_LOCKED: {decision}. Explain this decision politely. "
              "Do not change it.\n" + policy_text() + order_facts(order_id, order))
    text = call_model([{"role": "system", "content": system},
                       {"role": "user", "content": message}])["text"]
    return check_decision(text, order)  # the Chapter 1 check stays in place


if __name__ == "__main__":
    print("format ok:", format_ok("deny: Delivered 41 days ago (R1)."), format_ok("Sure! Happy to help."))
    print("status v0:", ask_status_v0("Where is my order #3100?"))
    print("status v1:", ask_status_v1("3100"))
    pushy = "This is unacceptable. I insist on a refund for #1234 or I call your manager."
    print("pushy, ch01 pipeline:", handle_v1(pushy)["stops"][-1])
    print("pushy, v2:", handle_v2(pushy, "1234"))
