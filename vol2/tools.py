"""Chapter 2: tool engineering. A tool is an API whose caller guesses.

MM-095 A Tool Is an API for a Model: a spec (name, what it does, args, what each
       error means), validation on the way in AND out, error classes with a next step.
MM-096 Blast Radius: write tools get a cap, a preview, a precondition checked inside
       the tool, and a required idempotency key.
"""
from dataclasses import dataclass, field
from typing import Callable, Optional

from world import WorldError

CAP_INR = 5000            # R4: refunds above INR 5,000 need a human agent's approval


class BadArg(ValueError):
    pass


def canon(kind, value):
    """One spelling per value: '#2001' -> '2001'; 'INR 950', 'Rs. 950', '950.00' -> 950."""
    text = str(value).strip()
    if kind == "order_id":
        text = text.lstrip("#").strip()
        if not text.isdigit():
            raise BadArg(f"order_id must be digits like 2001, got {value!r}")
        return text
    if kind == "inr":
        for mark in ("INR", "Rs.", "Rs", ","):
            text = text.replace(mark, "")
        try:
            number = float(text.strip())
        except ValueError:
            raise BadArg(f"amount must be whole rupees like 950, got {value!r}") from None
        if number != int(number) or number <= 0:
            raise BadArg(f"amount must be whole rupees above 0, got {value!r}")
        return int(number)
    if kind == "text":
        if not text:
            raise BadArg("text must not be empty")
        return text
    raise BadArg(f"unknown kind {kind}")


@dataclass
class Spec:
    name: str
    does: str                         # what it does, for the model to read
    args: dict                        # arg name -> kind (order_id | inr | text)
    errors: dict                      # code -> (error class, next step)
    run: Callable                     # run(world, args, key) -> receipt
    writes: bool = False
    cap_inr: Optional[int] = None     # blast radius: largest amount without approval
    precondition: Optional[Callable] = None   # (world, args) -> error code or None
    exposure: Optional[Callable] = None       # (world, args) -> INR the cap counts
    preview: Optional[Callable] = None        # (world, args) -> text
    receipt_fields: tuple = ()        # what a good reply must contain
    checks_out: list = field(default_factory=list)  # (args, receipt) -> bool

    def card(self):
        """The instruction card the model reads."""
        errs = "; ".join(f"{c}: {nxt}" for c, (_, nxt) in self.errors.items())
        return (f"{self.name}({', '.join(f'{a}: {k}' for a, k in self.args.items())})"
                f" - {self.does} Errors: {errs}")


COMMON = {"BAD_ARGS": ("business", "fix the arguments as the message says"),
          "NOT_YOUR_ORDER": ("business", "escalate: do not retry"),
          "MISSING_KEY": ("business", "the harness must supply an idempotency key"),
          "TIMEOUT": ("transient", "retry with the same key"),
          "BAD_TOOL_OUTPUT": ("business", "escalate: the tool reply failed its check")}


def fail(spec, code, detail=""):
    cls, nxt = spec.errors.get(code) or COMMON.get(code) or ("business", "escalate")
    return {"ok": False, "error": code, "class": cls, "next_step": nxt,
            "detail": detail}


def call(spec, world, session, raw_args, key=None, dry_run=False, approved=False):
    """The tool contract, in the order it is checked."""
    # 1. inputs: only known args, each in its one canonical spelling
    unknown = set(raw_args) - set(spec.args)
    missing = set(spec.args) - set(raw_args)
    if unknown or missing:
        return fail(spec, "BAD_ARGS", f"unknown={sorted(unknown)} missing={sorted(missing)}")
    try:
        args = {a: canon(kind, raw_args[a]) for a, kind in spec.args.items()}
    except BadArg as e:
        return fail(spec, "BAD_ARGS", str(e))
    # 2. authorization inside the tool: the session's customer,
    #    never the model's claim
    order = (world.order(args["order_id"])
             if "order_id" in args else None)
    if "order_id" in args and (
            order is None or order["owner"] != session.customer_id):
        return fail(spec, "NOT_YOUR_ORDER")
    # 3. write preconditions, checked against the world as it is now.
    #    A retry of an operation that already landed (same key) gets
    #    its original receipt.
    replay = spec.writes and key in getattr(world, "by_key", {})
    if spec.precondition and not replay:
        code = spec.precondition(world, args)
        if code:
            return fail(spec, code)
    # 4. blast radius: cap, then preview, then a required key
    at_risk = (spec.exposure(world, args) if spec.exposure
               else args.get("amount_inr", 0))
    if (spec.cap_inr is not None and at_risk > spec.cap_inr
            and not replay and not approved):
        return fail(spec, "AMOUNT_OVER_CAP",
                    f"INR {at_risk:,} > INR {spec.cap_inr:,}")
    if dry_run:
        return {"ok": True, "preview": spec.preview(world, args),
                "reserved": False}
    if spec.writes and not key:
        return fail(spec, "MISSING_KEY")
    try:
        receipt = spec.run(world, args, key)
    except WorldError as e:
        return fail(spec, e.code)
    # 5. outputs: the tool's own reply is checked too
    if any(f not in receipt for f in spec.receipt_fields) or not all(
            check(args, receipt) for check in spec.checks_out):
        return fail(spec, "BAD_TOOL_OUTPUT", str(receipt))
    return {"ok": True, "receipt": receipt}


# ---- issue_refund ------------------------------------------------------------
def _refund_pre(world, args):
    order = world.order(args["order_id"])
    if world.payments_for(args["order_id"]):
        return "ALREADY_REFUNDED"
    if args["amount_inr"] != order["amount"]:      # no partial refunds: a split
        return "AMOUNT_NOT_ORDER_TOTAL"            # must not slip under the cap
    return None


def _refund_exposure(world, args):
    """The cap counts the whole order, so INR 12,500 cannot go out as 5,000 + 7,500."""
    return max(args["amount_inr"], world.order(args["order_id"])["amount"])


ISSUE_REFUND = Spec(
    name="issue_refund",
    does="Refund a delivered order to the original payment method, once.",
    args={"order_id": "order_id", "amount_inr": "inr"},
    errors={"AMOUNT_NOT_ORDER_TOTAL": ("business",
                                       "refund exactly the order amount, or request_approval"),
            "ALREADY_REFUNDED": ("business", "tell the customer it is already refunded"),
            "AMOUNT_OVER_CAP": ("business", "request_approval"),
            "TIMEOUT": ("transient", "retry with the same key")},
    run=lambda world, a, key: world.refund(a["order_id"], a["amount_inr"], key=key),
    writes=True, cap_inr=CAP_INR, precondition=_refund_pre, exposure=_refund_exposure,
    preview=lambda world, a: f"INR {a['amount_inr']:,} on #{a['order_id']}",
    receipt_fields=("receipt_id", "order_id", "amount"),
    checks_out=[lambda a, r: r["order_id"] == a["order_id"]
                and r["amount"] == a["amount_inr"]])

LOOK_UP_ORDER = Spec(
    name="look_up_order",
    does="Read one order: item, amount in INR, damaged flag.",
    args={"order_id": "order_id"}, errors={},
    run=lambda world, a, key: {k: world.order(a["order_id"])[k]
                               for k in ("order_id", "item", "amount", "damaged")},
    receipt_fields=("order_id", "amount"))

SPECS = {s.name: s for s in (ISSUE_REFUND, LOOK_UP_ORDER)}


def refund_key(ticket_id, order_id):
    """One operation, one key: the same ticket refunding the same order reuses it."""
    return f"k-{ticket_id}-refund-{order_id}"


# ---- the old tool (Vol 1 style), kept to show what goes wrong ---------------------
def old_issue_refund(world, order_id, amount):
    world.orders[order_id]                    # "#2001" -> KeyError, a raw traceback
    return world.refund(order_id, int(float(amount)))   # no cap, no check, no key
