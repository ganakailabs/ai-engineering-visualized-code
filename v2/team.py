"""Chapter 14: an orchestrator, three worker desks, an owned board and one budget.

The same eight tickets run three ways on the same world:
  workflow   code routes by keyword; workers are code (no model call)
  one agent  one model call per ticket names the kind, order and item
  team       an orchestrator call routes; the refunds and products desks each make
             their own model call
Every way ends at the same commit checks, so a wrong fact is refused, not acted on.

Board: one writer per field, a version on every field (a stale write is refused) and
a check at commit (a typed field can still hold a wrong fact).
Budget: one pool of steps and simulated minutes per ticket; a delegate spends the
parent's pool, and cancel() reaches every worker that holds it.
Equal outcomes on the stub show the wiring is consistent, nothing more.
"""
import re
from datetime import timedelta

import llm
from world import TODAY, World

OWNER = {"order_id": "orchestrator", "decision": "refunds",
         "tracking": "shipping", "stock": "products"}      # one writer per field

TICKETS = [  # (ticket id, text, expected outcome); all from customer asha
    ("T1", "My mug set from order 2001 arrived cracked. Refund please.", "refunded 2001 INR 950"),
    ("T2", "Where is order 6001?", "track 6001 in transit"),
    ("T3", "Is the blue mug set back in stock?", "stock mug set blue 0"),
    ("T4", "Refund the clearance jacket, order 4410.", "human"),
    ("T5", "Has order 5120 shipped yet?", "track 5120 packing"),
    ("T6", "Refund order 3100 please.", "human"),
    ("T7", "Do you have the green mug set?", "stock mug set green 4"),
    ("T8", "Order 1234, the desk lamp: I want my money back.", "human"),
]
ITEMS = ["mug set blue", "mug set green"]


class Refused(Exception):
    pass


class Exhausted(Exception):
    pass


class Budget:
    """One pool per ticket. child() hands a worker the same pool, not a new one."""

    def __init__(self, world, steps, minutes, who="orchestrator", pool=None):
        self.world, self.who = world, who
        self.pool = pool or {"steps": steps, "until": world.clock + timedelta(minutes=minutes),
                             "cancelled": False, "spent": {}}

    def child(self, who):
        return Budget(self.world, 0, 0, who=who, pool=self.pool)

    def spend(self, what):
        p = self.pool
        if p["cancelled"]:
            raise Exhausted(f"{self.who}: cancelled")
        if p["steps"] <= 0 or self.world.clock >= p["until"]:
            p["cancelled"] = True                  # the first to hit the wall stops all
            raise Exhausted(f"{self.who}: budget exhausted before {what}")
        p["steps"] -= 1
        p["spent"][self.who] = p["spent"].get(self.who, 0) + 1
        self.world.tick()

    def cancel(self):
        self.pool["cancelled"] = True

    @property
    def left(self):
        return self.pool["steps"]


class Board:
    """Shared facts for one ticket: owned fields, versions, checked at commit."""

    def __init__(self, world, customer, ticket):
        self.world, self.customer, self.ticket = world, customer, ticket
        self.facts, self.version, self.log = {}, {}, []

    def read(self, field):
        return self.facts.get(field), self.version.get(field, 0)

    def write(self, field, value, by, seen):
        if OWNER[field] != by:
            raise self._refuse(f"board write by={by} field={field} -> refused not owner")
        have = self.version.get(field, 0)
        if seen != have:
            raise self._refuse(f"board write by={by} field={field} -> refused "
                               f"version conflict (saw v={seen}, board has v={have})")
        ok, why = self.check(field, value)
        if not ok:
            raise self._refuse(f"board write {field}={value} by={by} -> refused {why}")
        self.facts[field], self.version[field] = value, have + 1
        self.log.append(f"board write {field}={value} owner={by} v={have + 1}")
        return have + 1

    def _refuse(self, line):
        self.log.append(line)
        return Refused(line)

    def check(self, field, value):
        """Verified at commit: the type is not enough; the fact must be true."""
        if field == "order_id":
            o = self.world.order(value)
            if value not in re.findall(r"\d{4}", self.ticket):
                return False, "not in the ticket"
            if not o or o.get("owner") != self.customer:
                return False, "not this customer's order"
        if field == "decision" and value != "human":
            o = self.world.order(self.facts.get("order_id"))
            ok, why = eligible(o)
            if not ok:
                return False, why
        return True, ""


def eligible(o):
    if o is None:
        return False, "no order"
    if o["final_sale"]:
        return False, "final sale"
    if o["delivered"] is None or (TODAY - o["delivered"]).days > 30:
        return False, "outside the 30-day window"
    return True, ""


# ---- model turns (stub scripts first, then the call) -----------------------
def _tid(user):
    return re.search(r"Ticket (T\d)", user).group(1)


STUB_ONE = {"T1": ("refund", "2001", None), "T2": ("track", "6001", None),
            "T3": ("stock", None, "mug set blue"), "T4": ("refund", "4410", None),
            "T5": ("track", "5120", None), "T6": ("refund", "3100", None),
            "T7": ("stock", None, "mug set green"), "T8": ("refund", "1234", None)}
DESK = {"refund": "refunds", "track": "shipping", "stock": "products"}

ONE_SYS = ("You are a store support agent. Read the ticket and reply with JSON only: "
           '{"kind": "refund" | "track" | "stock" | "human", "order_id": "four digits" '
           'or null, "item": "mug set blue" | "mug set green" | null}.')
ROUTE_SYS = ("You are a dispatcher. Send the ticket to one desk. Reply with JSON only: "
             '{"to": "refunds" | "shipping" | "products" | "human", '
             '"order_id": "four digits" or null}.')
REFUND_SYS = ("You are the refunds desk. Given an order and the ticket, decide. Reply "
              'with JSON only: {"decision": "refund" | "human", "reason": "..."}.')
PRODUCT_SYS = ("You are the products desk. Name the item asked about. Reply with JSON "
               'only: {"item": "mug set blue" | "mug set green" | null}.')


def ask(budget, system, user, stub):
    budget.spend("model call")
    move, raw = llm.ask_json(system, user, stub)
    return move if isinstance(move, dict) else {}


def _oid(v):
    v = str(v or "").lstrip("#")
    return v if re.fullmatch(r"\d{4}", v) else None


# ---- the desks: tools in code, behind the board ------------------------------
def refunds_desk(world, board, budget, tid, text, use_model):
    b = budget.child("refunds")
    oid, _ = board.read("order_id")
    b.spend("look_up_order")
    o = world.order(oid)
    if use_model:
        move = ask(b, REFUND_SYS, f"Ticket {tid}: {text}\nOrder: {o}",
                   lambda u: {"decision": "refund" if eligible(o)[0] else "human"})
        want = move.get("decision") if move.get("decision") in ("refund", "human") else "human"
    else:
        want = "refund" if eligible(o)[0] else "human"
    try:
        board.write("decision", want, "refunds", board.read("decision")[1])
    except Refused:
        board.write("decision", "human", "refunds", board.read("decision")[1])
    if board.read("decision")[0] != "refund":
        return "human"
    b.spend("refund")
    world.refund(oid, o["amount"], key=f"{tid}-refund")
    return f"refunded {oid} INR {o['amount']}"


def shipping_desk(world, board, budget, tid, text, use_model):
    b = budget.child("shipping")
    oid, _ = board.read("order_id")
    b.spend("look_up_shipment")
    status = world.shipment(oid)
    if status is None:
        return "human"
    board.write("tracking", status, "shipping", 0)
    return f"track {oid} {status}"


def products_desk(world, board, budget, tid, text, use_model, item=None):
    b = budget.child("products")
    if use_model:
        move = ask(b, PRODUCT_SYS, f"Ticket {tid}: {text}",
                   lambda u: {"item": STUB_ONE[_tid(u)][2]})
        item = move.get("item")
    if item not in ITEMS:
        return "human"
    b.spend("stock_of")
    n = world.stock_of(item)
    board.write("stock", n, "products", 0)
    return f"stock {item} {n}"


DESKS = {"refunds": refunds_desk, "shipping": shipping_desk, "products": products_desk}


def run_ticket(world, mode, tid, text, steps=10, minutes=30, customer="asha"):
    """Returns (outcome, budget, board)."""
    board, budget = Board(world, customer, text), Budget(world, steps, minutes)
    item = None
    try:
        if mode == "workflow":
            low = text.lower()
            desk = ("refunds" if "refund" in low or "money back" in low else
                    "products" if "stock" in low or "have the" in low else "shipping")
            oid = (re.findall(r"\d{4}", text) or [None])[0]
            item = next((i for i in ITEMS if i.split()[-1] in low), None)
        elif mode == "one agent":
            move = ask(budget, ONE_SYS, f"Ticket {tid}: {text}",
                       lambda u: dict(zip(("kind", "order_id", "item"), STUB_ONE[_tid(u)])))
            desk, oid, item = DESK.get(move.get("kind")), _oid(move.get("order_id")), move.get("item")
        else:
            move = ask(budget, ROUTE_SYS, f"Ticket {tid}: {text}",
                       lambda u: {"to": DESK[STUB_ONE[_tid(u)][0]],
                                  "order_id": STUB_ONE[_tid(u)][1]})
            desk, oid = move.get("to"), _oid(move.get("order_id"))
        if desk not in DESKS:
            return "human", budget, board
        if desk != "products":
            board.write("order_id", oid, "orchestrator", 0)
        if mode == "team":
            return DESKS[desk](world, board, budget, tid, text, True), budget, board
        if desk == "products":
            return products_desk(world, board, budget, tid, text, False, item), budget, board
        return DESKS[desk](world, board, budget, tid, text, False), budget, board
    except (Refused, Exhausted) as e:
        board.log.append(f"stop {e}") if isinstance(e, Exhausted) else None
        return "human", budget, board


def run_all(mode, steps=10):
    world, rows = World(), []
    for tid, text, want in TICKETS:
        out, budget, board = run_ticket(world, mode, tid, text, steps=steps)
        rows.append({"tid": tid, "out": out, "want": want, "steps": steps - budget.left,
                     "spent": dict(budget.pool["spent"]), "log": board.log})
    return world, rows


def telephone(typed):
    """BREAK (typed=False): the orchestrator hands the refunds desk a free-text summary
    that drifted (#2001 became #2077), and the desk parses the id out of it.
    FIX (typed=True): the id goes on the board as an owned field, checked at commit."""
    world, (tid, text, _) = World(), TICKETS[0]
    summary = "Asha wants a refund for her damaged order #2077."   # the drift
    board, budget = Board(world, "asha", text), Budget(world, 10, 30)
    oid = re.findall(r"\d{4}", summary)[0]
    if typed:
        try:
            board.write("order_id", oid, "orchestrator", 0)
        except Refused:
            return world, summary, board, "human"
    else:
        board.facts["order_id"] = oid          # free text: nobody checks it
    return world, summary, board, refunds_desk(world, board, budget, tid, text, False)
