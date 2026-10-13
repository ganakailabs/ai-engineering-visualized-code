"""Chapter 20: Planning and Multi-Step Tasks."""
import json

from stub_model import call_model
from store import STOCK


# The steps a plan may use. Your code runs them.
def check_stock(item):
    n = STOCK.get(item, 0)
    return f"in stock: {n}" if n else f"surprise: {item} is out of stock"


def reserve(item):
    return f"reserved one {item}"


def send_label(order_id):
    return f"return label sent for #{order_id}"


def ask_customer(question):
    return f"asked the customer: {question}"


STEPS = {"check_stock": check_stock, "reserve": reserve,
         "send_label": send_label, "ask_customer": ask_customer}
PLANNER = ("Write a plan for this ticket as a JSON list of steps, "
           "each with a tool and args. Tools: " + ", ".join(STEPS) + ".")


# MM-054: plan, then execute
def make_plan(ticket, model=call_model, surprise=""):
    note = f"\nSURPRISE: {surprise}" if surprise else ""
    r = model([{"role": "system", "content": PLANNER},
               {"role": "user", "content": ticket + note}])
    return json.loads(r["text"])


def check_plan(plan):
    """Check the whole plan before any step acts."""
    for step in plan:
        if step["tool"] not in STEPS:
            return f"unknown tool {step['tool']}"
    if len(plan) > 5:
        return "plan too long for one ticket"
    return None


# MM-055: replan on surprise, at most once
def run(ticket, model=call_model, replans=1):
    plan, log = make_plan(ticket, model), []
    while True:
        log.append(("plan", [s["tool"] for s in plan]))
        problem = check_plan(plan)
        if problem:
            return log + [("escalate", problem)]
        for step in plan:
            out = STEPS[step["tool"]](**step["args"])
            log.append((step["tool"], out))
            if out.startswith("surprise"):
                break               # stop: the plan is now wrong
        else:
            return log              # every step ran
        if replans == 0:
            return log + [("escalate", "replan limit reached")]
        replans -= 1
        plan = make_plan(ticket, model, surprise=out)


if __name__ == "__main__":
    for colour in ("green", "blue"):
        t = f"Please swap my mug set #2001 for the {colour} one."
        print(t)
        for what, out in run(t):
            print(f"  {what:12} {out}")
