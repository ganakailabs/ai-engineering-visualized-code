"""The shared Vol 2 mock world (decision D2-5): one fictional Northwind Goods store.

Every Vol 2 chapter and test drives this one world: orders with owners, shipments,
stock, a courier, payments, a simulated clock and scripted faults. It is a mock, so
nothing here is model or production performance; it is the ground truth that tests
inspect (series contract section 2: assert on state and receipts, not on trace lines).

Facts come from Vol 1's store.py. Owners are fixture data added for Vol 2
(series contract section 3): asha owns her orders; #3100 belongs to customer c-42.
"""
import copy

import _root  # noqa: F401  (Vol 1 store.py)
from datetime import datetime, timedelta

from store import CARRIER_REDIRECT, ORDERS, SHIPMENTS, STOCK, TODAY

OWNERS = {"1234": "asha", "2001": "asha", "4410": "asha", "5120": "asha",
          "6001": "asha", "3100": "c-42", "2077": "asha"}  # fixture addition


class WorldError(Exception):
    """A failure the world reports. transient=True means a retry may work."""

    def __init__(self, code, transient=False):
        super().__init__(code)
        self.code, self.transient = code, transient


FIXTURE_ORDERS = {                                           # fixture addition
    "5120": {"item": "Table fan", "amount": 2400, "delivered": None,
             "final_sale": False, "damaged": False},
    "6001": {"item": "Backpack", "amount": 1600, "delivered": None,
             "final_sale": False, "damaged": False},
    "2077": {"item": "Steel water bottle", "amount": 700,            # Ch 8 (SC-013)
             "delivered": TODAY - timedelta(days=2), "final_sale": False, "damaged": True},
}


class LostReply(Exception):
    """Scripted fault: the write happened, but its reply never arrived."""


class World:
    def __init__(self, stock=None, faults=None):
        self.orders = copy.deepcopy(ORDERS)
        self.orders.update(copy.deepcopy(FIXTURE_ORDERS))
        for oid, owner in OWNERS.items():
            self.orders[oid]["owner"] = owner
        for o in self.orders.values():
            o["version"] = 1                  # bumped by every edit (Chapter 8)
        self.shipments = dict(SHIPMENTS)
        self.redirect = dict(CARRIER_REDIRECT)
        self.stock = dict(STOCK if stock is None else stock)
        self.addresses = {}
        self.payments, self.labels, self.pickups = [], [], []
        self.dropoffs, self.cancelled = [], []
        self.carrier_asks = 0
        self.calls = []                       # every write that reached the world
        self.by_key = {}                      # idempotency key -> (op, args, receipt)
        self.key_seen = {}                    # idempotency key -> when it was stored
        self.payment_keys = {}                # receipt_id -> key (the payments record)
        self.cancelled_pickups = []
        self.clock = datetime(TODAY.year, TODAY.month, TODAY.day, 10, 0)
        self.faults = {op: list(seq) for op, seq in (faults or {}).items()}
        self._n = 0

    # ---- time and faults -------------------------------------------------
    def tick(self, minutes=1):
        self.clock += timedelta(minutes=minutes)

    def now(self):
        return self.clock.isoformat(timespec="seconds")

    def inject(self, op, fault):
        """Script a fault: the next call to `op` hits it (e.g. 'OUT_OF_STOCK')."""
        self.faults.setdefault(op, []).append(fault)

    def _fault(self, op):
        queue = self.faults.get(op)
        if queue:
            code = queue.pop(0)
            if code in ("SELL_OUT", "LOST_REPLY", "GHOST"):   # handled by the operation
                return code
            raise WorldError(code, transient=code in ("TIMEOUT", "COURIER_UNAVAILABLE"))
        return None

    def _id(self, prefix):
        self._n += 1
        return f"{prefix}-{self._n:03d}"

    def _write(self, op, args, key, do):
        """Run a write once per idempotency key. Same key, same args: same receipt."""
        self.tick()
        if key is not None and key in self.by_key:
            old_op, old_args, receipt = self.by_key[key]
            if (old_op, old_args) != (op, args):
                raise WorldError("KEY_REUSED_WITH_OTHER_ARGS")
            return dict(receipt, replayed=True)
        try:
            receipt = do()
        except LostReply as lost:            # the write landed; the reply is lost
            self.calls.append((op, dict(args)))
            if key is not None:
                self.by_key[key] = (op, dict(args), lost.args[0])
                self.key_seen[key] = self.clock
            raise WorldError("TIMEOUT", transient=True) from None
        self.calls.append((op, dict(args)))
        if key is not None:
            self.by_key[key] = (op, dict(args), receipt)
            self.key_seen[key] = self.clock
        return dict(receipt)

    def prune_keys(self, keep_hours=24):
        """The receiver forgets dedup keys older than its retention (Chapter 6)."""
        for key, seen in list(self.key_seen.items()):
            if self.clock - seen > timedelta(hours=keep_hours):
                del self.by_key[key], self.key_seen[key]

    def edit_order(self, order_id, **changes):
        """Scripted event: a teammate edits an order; its version goes up (Chapter 8)."""
        self.tick()
        self.orders[order_id].update(changes)
        self.orders[order_id]["version"] += 1

    # ---- reads -----------------------------------------------------------
    def order(self, order_id):
        o = self.orders.get(order_id)
        return dict(o, order_id=order_id) if o else None

    def shipment(self, order_id):
        return self.shipments.get(order_id)

    def stock_of(self, item):
        self.tick()
        return self.stock.get(item, 0)

    # ---- writes ----------------------------------------------------------
    def refund(self, order_id, amount, key=None):
        def do():
            fault = self._fault("refund")
            lost = fault == "LOST_REPLY"
            p = {"receipt_id": self._id("pay"), "order_id": order_id,
                 "amount": amount, "at": self.now()}
            if fault == "GHOST":              # the tool says paid; nothing was recorded
                return dict(p)
            self.payments.append(p)
            self.payment_keys[p["receipt_id"]] = key
            if lost:
                raise LostReply(dict(p))
            return dict(p)
        return self._write("refund", {"order_id": order_id, "amount": amount}, key, do)

    def change_address(self, order_id, address, key=None):
        def do():
            if self.shipments.get(order_id) != "packing":
                raise WorldError("TOO_LATE_TO_CHANGE")
            self.addresses[order_id] = address
            return {"receipt_id": self._id("adr"), "order_id": order_id}
        return self._write("change_address", {"order_id": order_id,
                                              "address": address}, key, do)

    def ask_carrier(self, order_id):
        self.tick()
        self.carrier_asks += 1
        return bool(self.redirect.get(order_id, False))

    def ship(self, order_id):
        """Scripted event: the warehouse hands the parcel to the courier."""
        self.tick()
        self.shipments[order_id] = "in transit"

    def cancel_order(self, order_id, key=None):
        def do():
            if self.shipments.get(order_id) != "packing":
                raise WorldError("ALREADY_SHIPPED")
            self.cancelled.append(order_id)
            self.shipments[order_id] = "cancelled"
            return {"receipt_id": self._id("can"), "order_id": order_id}
        return self._write("cancel_order", {"order_id": order_id}, key, do)

    def send_label(self, order_id, item, key=None):
        def do():
            self._fault("send_label")
            lab = {"receipt_id": self._id("lbl"), "order_id": order_id,
                   "item": item, "status": "live"}
            self.labels.append(lab)
            return dict(lab)
        return self._write("send_label", {"order_id": order_id, "item": item}, key, do)

    def void_label(self, receipt_id, key=None):
        def do():
            for lab in self.labels:
                if lab["receipt_id"] == receipt_id:
                    lab["status"] = "void"
                    return {"receipt_id": self._id("vod"), "voided": receipt_id}
            raise WorldError("NO_SUCH_LABEL")
        return self._write("void_label", {"receipt_id": receipt_id}, key, do)

    def book_pickup(self, order_id, item, key=None):
        """Book the courier and reserve the replacement unit."""
        def do():
            if self._fault("book_pickup") == "SELL_OUT":
                self.stock[item] = 0
            if self.stock.get(item, 0) < 1:
                raise WorldError("OUT_OF_STOCK")
            self.stock[item] -= 1
            p = {"receipt_id": self._id("pik"), "order_id": order_id, "item": item}
            self.pickups.append(p)
            return dict(p)
        return self._write("book_pickup", {"order_id": order_id, "item": item}, key, do)

    def partner_dropoff(self, order_id, item, key=None):
        """The customer drops the parcel at a partner store; reserves the unit."""
        def do():
            if self.stock.get(item, 0) < 1:
                raise WorldError("OUT_OF_STOCK")
            self.stock[item] -= 1
            d = {"receipt_id": self._id("drp"), "order_id": order_id, "item": item}
            self.dropoffs.append(d)
            return dict(d)
        return self._write("partner_dropoff", {"order_id": order_id, "item": item}, key, do)

    def cancel_pickup(self, receipt_id, key=None):
        """Compensation for book_pickup: a new action that can fail (Chapter 6)."""
        def do():
            self._fault("cancel_pickup")      # e.g. ALREADY_COLLECTED: it can fail
            for p in self.pickups:
                if p["receipt_id"] == receipt_id:
                    self.pickups.remove(p)
                    self.stock[p["item"]] = self.stock.get(p["item"], 0) + 1
                    self.cancelled_pickups.append(receipt_id)
                    return {"receipt_id": self._id("cxp"), "cancelled": receipt_id}
            raise WorldError("NO_SUCH_PICKUP")
        return self._write("cancel_pickup", {"receipt_id": receipt_id}, key, do)

    def find_payment(self, key):
        """Reconcile: read the payments record itself, which outlives dedup keys."""
        for p in self.payments:
            if self.payment_keys.get(p["receipt_id"]) == key:
                return dict(p)
        return None

    # ---- counters tests read ----------------------------------------------
    def payments_for(self, order_id):
        return [p for p in self.payments if p["order_id"] == order_id]

    def live_labels(self, order_id):
        return [lab for lab in self.labels
                if lab["order_id"] == order_id and lab["status"] == "live"]

    def write_calls(self, op):
        return [a for o, a in self.calls if o == op]
