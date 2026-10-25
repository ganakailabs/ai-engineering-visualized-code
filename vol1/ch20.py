"""Chapter 20: Planning and Multi-Step Tasks."""
import json

from parse import first_json, warn
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
    plan = first_json(r["text"])         # tolerant; None if no JSON
    if isinstance(plan, dict):           # JSON mode wraps lists: {"steps": []}
        plan = plan.get("steps")
    if not isinstance(plan, list):
        warn(f"plan is not a JSON list of steps: {r['text'][:60]!r}")
        return None
    return plan


ARGS = {"check_stock": {"item"}, "reserve": {"item"},
        "send_label": {"order_id"}, "ask_customer": {"question"}}


def check_plan(plan, ticket=""):
    """Check the whole plan before any step acts: names, args, order, task."""
    if not isinstance(plan, list) or len(plan) > 5:
        return "plan must be a list of at most 5 steps"
    checked = set()
    for step in plan:
        if not isinstance(step, dict):
            return "each step must be a JSON object"
        tool, args = step.get("tool"), step.get("args")
        if tool not in STEPS:
            return f"unknown tool {tool}"
        if not isinstance(args, dict) or set(args) != ARGS[tool]:
            return f"{tool} needs exactly {sorted(ARGS[tool])}"
        if tool == "check_stock":
            checked.add(args["item"])
        if tool == "reserve" and args["item"] not in checked:
            return f"reserve {args['item']} before check_stock"
        oid = args.get("order_id")
        if tool == "send_label" and f"#{oid}" not in ticket:
            return f"order #{oid} is not in this ticket"
    return None


# MM-055: replan on surprise, at most once. Completed steps are never re-run.
def run(ticket, model=call_model, replans=1):
    plan, log, done = make_plan(ticket, model), [], set()
    while True:
        log.append(("plan", [s.get("tool") if isinstance(s, dict) else s
                             for s in plan or []]))
        problem = check_plan(plan, ticket)
        if problem:
            return log + [("escalate", problem)]
        for step in plan:
            key = json.dumps(step, sort_keys=True)
            if key in done:
                log.append((step["tool"], "skipped: already done"))
                continue
            out = STEPS[step["tool"]](**step["args"])
            done.add(key)
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
    unsafe = lambda messages, **kw: {"text": json.dumps(
        [{"tool": "reserve", "args": {"item": "mug set green"}}])}
    print("known tool, wrong order:", run(t, model=unsafe)[-1])
