"""Chapter 3: planning with a task tree, a dependency graph, a checker and repair.

MM-097 The Task Tree: the TREE says what the goal breaks into; the dependency
       ARROWS ('after') say what must finish first. check_plan() runs before any step.
MM-098 Plan Repair: repair only the broken branch; keep finished steps whose inputs
       still hold, and compensate the ones that no longer do.
"""
import json

from store import STOCK
from tools import BadArg, canon
from world import WorldError

ITEMS = set(STOCK)                    # 'mug set blue', 'mug set green'


def item(value):
    if value not in ITEMS:
        raise BadArg(f"item must be one of {sorted(ITEMS)}, got {value!r}")
    return value


# Each step tool: argument kinds, the facts it reads, and how to undo its effect.
STEP_TOOLS = {
    "verify_order": {"args": {"order_id": "order_id"}, "reads": ["order"]},
    "check_stock": {"args": {"item": "item"}, "reads": ["stock"]},
    "choose": {"args": {"item": "item"}, "reads": [], "decision": True},
    "send_label": {"args": {"order_id": "order_id", "item": "item"}, "reads": [],
                   "undo": "void_label"},
    "book_pickup": {"args": {"order_id": "order_id", "item": "item"},
                    "reads": ["stock", "courier"]},
    "partner_dropoff": {"args": {"order_id": "order_id", "item": "item"},
                        "reads": ["stock"]},
    "reply": {"args": {"text": "text"}, "reads": [], "stop": True},
}
BRANCH = {"verify_order": "VERIFY ORDER", "check_stock": "CHECK STOCK",
          "choose": "CHOOSE", "send_label": "SEND LABEL", "book_pickup": "ARRANGE PICKUP",
          "partner_dropoff": "ARRANGE PICKUP", "reply": "REPLY"}
SUBGOAL = {"VERIFY ORDER": "confirm", "CHECK STOCK": "pick replacement",
           "CHOOSE": "pick replacement", "SEND LABEL": "return and swap",
           "ARRANGE PICKUP": "return and swap", "REPLY": "close"}


def typed(tool, args):
    spec = STEP_TOOLS[tool]["args"]
    if set(args) != set(spec):
        raise BadArg(f"{tool} takes {sorted(spec)}, got {sorted(args)}")
    return {a: (item(args[a]) if k == "item" else canon(k, args[a]))
            for a, k in spec.items()}


def check_plan(plan):
    """Every rule in code, before any step runs. Returns a list of problems."""
    steps = plan.get("steps") if isinstance(plan, dict) else None
    if not isinstance(steps, list) or not steps or len(steps) > 10:
        return ["plan must be a list of 1-10 steps"]
    problems, ids = [], [s.get("id") for s in steps if isinstance(s, dict)]
    if len(ids) != len(steps) or len(set(ids)) != len(ids):
        return ["every step needs a unique id"]
    for s in steps:
        if s.get("tool") not in STEP_TOOLS:
            problems.append(f"{s['id']}: unknown tool {s.get('tool')!r}")
            continue
        try:
            s["args"] = typed(s["tool"], s.get("args") or {})
        except (BadArg, AttributeError, TypeError) as e:
            problems.append(f"{s['id']}: {e}")
        if not isinstance(s.get("after", []), list):
            problems.append(f"{s['id']}: 'after' must be a list")
            s["after"] = []
        for dep in s.setdefault("after", []):
            if dep not in ids:
                problems.append(f"{s['id']}: waits for unknown step {dep!r}")
    if problems:
        return problems
    if order(steps) is None:
        return ["the dependency arrows form a cycle"]
    stops = [s for s in steps if s["tool"] == "reply"]
    if len(stops) != 1:
        return ["the plan needs exactly one reply step "
                "(its stop condition)"]
    reply_id = stops[0]["id"]
    if set(ancestors(steps, reply_id)) != set(ids) - {reply_id}:
        return ["the reply step must wait for every other step"]
    chosen = [s for s in steps if s["tool"] == "choose"]
    if len(chosen) != 1:
        return ["the plan needs exactly one choose step"]
    by_id = {s["id"]: s for s in steps}
    # every write ships the item that was chosen
    for s in steps:
        if s["tool"] in ("send_label", "book_pickup",
                         "partner_dropoff"):
            if chosen[0]["id"] not in ancestors(steps, s["id"]):
                return [f"{s['id']}: must wait for the choose step"]
            chosen_item = by_id[chosen[0]["id"]]["args"]["item"]
            if s["args"]["item"] != chosen_item:
                return [f"{s['id']}: ships {s['args']['item']!r}, "
                        "not the chosen item"]
    return []


def order(steps):
    """Kahn's topological sort; None if the arrows form a cycle."""
    after = {s["id"]: set(s.get("after", [])) for s in steps}
    done, out = set(), []
    while len(out) < len(steps):
        ready = [s for s in steps if s["id"] not in done and after[s["id"]] <= done]
        if not ready:
            return None
        done.add(ready[0]["id"])
        out.append(ready[0])
    return out


def ancestors(steps, node_id):
    by_id = {s["id"]: s for s in steps}
    seen, todo = set(), list(by_id[node_id].get("after", []))
    while todo:
        n = todo.pop()
        if n not in seen and n in by_id:
            seen.add(n)
            todo += by_id[n].get("after", [])
    return seen


def descendants(steps, ids):
    out, grew = set(ids), True
    while grew:
        grew = False
        for s in steps:
            if s["id"] not in out and out & set(s.get("after", [])):
                out.add(s["id"])
                grew = True
    return out


def show_tree(steps, emit):
    """Print the decomposition tree, then the dependency arrows (they differ)."""
    groups = {}
    for s in steps:
        groups.setdefault(SUBGOAL[BRANCH[s["tool"]]], []).append(s)
    for goal, members in groups.items():
        emit("plan", f"{goal}: " + ", ".join(f"{s['id']} {BRANCH[s['tool']]}"
                                           for s in members))
    emit("plan", "edges " + " ".join(f"{d}->{s['id']}" for s in steps
                                     for d in s.get("after", [])))


# ---- running steps -------------------------------------------------------------
def node_key(ticket_id, step):
    """Stable per operation: the same step with the same args reuses its key."""
    return f"k-{ticket_id}-{step['tool']}-{json.dumps(step['args'], sort_keys=True)}"


def run_step(world, step, key):
    a = step["args"]
    if step["tool"] == "verify_order":
        o = world.order(a["order_id"])
        return {"order_id": a["order_id"], "item": o["item"], "damaged": o["damaged"]}
    if step["tool"] == "check_stock":
        n = world.stock_of(a["item"])
        if n < 1:
            raise WorldError("OUT_OF_STOCK")
        return {"item": a["item"], "in_stock": n}
    if step["tool"] == "choose":
        return {"chosen": a["item"]}
    if step["tool"] == "reply":
        return {"sent": a["text"]}
    return getattr(world, step["tool"])(a["order_id"], a["item"], key=key)


def execute(plan, world, ticket_id, emit, receipts=None, key_fn=node_key):
    """Run steps in dependency order. A step with a receipt for the same args is kept."""
    receipts = {} if receipts is None else receipts
    for step in order(plan["steps"]):
        held = receipts.get(step["id"])
        if held and held["args"] == step["args"]:
            continue
        try:
            receipt = run_step(world, step, key_fn(ticket_id, step))
        except WorldError as e:
            what = step["args"].get("item", "courier")
            emit("observe", f"surprise: {what} {e.code.lower().replace('_', ' ')}"
                 if e.code == "OUT_OF_STOCK" else f"surprise: {e.code}", code=e.code)
            return {"status": "surprise", "step": step, "code": e.code,
                    "receipts": receipts}
        receipts[step["id"]] = {"tool": step["tool"], "args": step["args"],
                                "receipt": receipt}
        emit("act", f"{step['id']} {step['tool']} " +
             " ".join(str(v) for v in step["args"].values()) +
             (f" -> {receipt['receipt_id']}" if "receipt_id" in receipt else ""))
    return {"status": "done", "receipts": receipts}


def broken_facts(step, code):
    if code == "OUT_OF_STOCK":
        return {("stock", step["args"].get("item"))}
    if code in ("COURIER_UNAVAILABLE", "TIMEOUT"):
        return {("courier", None)}
    return {("any", None)}


def reads(step, fact):
    kind, value = fact
    if kind == "any":
        return True
    return kind in STEP_TOOLS[step["tool"]]["reads"] and (
        value is None or value in step["args"].values())


def repair_scope(plan, receipts, failed, code):
    """Which steps still count, which are invalid, which need compensation."""
    steps, facts = plan["steps"], broken_facts(failed, code)
    hit = {s["id"] for s in steps if any(reads(s, f) for f in facts)} | {failed["id"]}
    invalid = descendants(steps, hit)
    kept = [s for s in steps if s["id"] in receipts and s["id"] not in invalid]
    undo = [s for s in steps if s["id"] in receipts and s["id"] in invalid
            and "undo" in STEP_TOOLS[s["tool"]]]
    decisions = [s for s in steps if s["id"] in invalid
                 and STEP_TOOLS[s["tool"]].get("decision")]
    branch = BRANCH[(decisions[0] if decisions else failed)["tool"]]
    return {"kept": kept, "invalid": invalid, "undo": undo, "branch": branch}
