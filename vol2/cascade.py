"""Chapter 15, MM-114: the error cascade, and the fix.

The courier and payments slow down together. A refund ticket (#2001, damaged) needs
a refund and a return label. Faults are scripted on the world, so every run is the
same and side effects are counted in the world, not in the trace.

BREAK: three layers (job, step, tool) each retry three times; no keys; no breaker.
       One slow courier becomes 27 calls and two labels; a lost payment reply is
       paid twice.
FIX:   one retry budget for the whole ticket, shared by every layer; a breaker per
       dependency; an idempotency key on every write; malformed output rejected;
       when the budget or the breaker says stop, an honest escalation.
"""
from world import World, WorldError

LATE = "LATE"            # the label is written, the reply times out
MALFORMED = "MALFORMED"  # the courier answers, with no receipt id


class Exhausted(Exception):
    pass


class Open(Exception):
    pass


class RetryBudget:
    """One pool of retries per ticket. Every layer takes from it; none has its own."""

    def __init__(self, retries, log):
        self.left, self.log = retries, log

    def take(self, layer, why):
        if self.left <= 0:
            self.log(f"budget retries_left=0 -> no retry at {layer} ({why})")
            raise Exhausted(why)
        self.left -= 1
        self.log(f"budget retry at {layer} ({why}) retries_left={self.left}")


class Breaker:
    """CLOSED -> OPEN after `threshold` failures in a row; OPEN refuses without calling;
    after `cool` simulated minutes it is HALF_OPEN and lets one trial call through.
    The trial closes it on success and reopens it on failure."""

    def __init__(self, name, world, log, threshold=3, cool=2):
        self.name, self.world, self.log = name, world, log
        self.threshold, self.cool = threshold, cool
        self.fails, self.opened_at, self.state = 0, None, "CLOSED"
        self.trials = 0

    def _now_state(self):
        if self.state == "OPEN":
            waited = (self.world.clock - self.opened_at).total_seconds() / 60
            if waited >= self.cool:
                self.state = "HALF_OPEN"
                self.log(f"breaker {self.name} HALF_OPEN after {waited:.0f} min")
        return self.state

    def call(self, fn):
        if self._now_state() == "OPEN":
            self.log(f"breaker {self.name} OPEN -> refused without calling")
            raise Open(self.name)
        if self.state == "HALF_OPEN":
            self.trials += 1
        try:
            out = fn()
        except WorldError:
            self.fails += 1
            if self.state == "HALF_OPEN" or self.fails >= self.threshold:
                self.state, self.opened_at = "OPEN", self.world.clock
                self.log(f"breaker {self.name} OPEN after {self.fails} failures")
            raise
        if self.state == "HALF_OPEN":
            self.log(f"breaker {self.name} CLOSED (trial succeeded)")
        self.state, self.fails = "CLOSED", 0
        return out


class SlowWorld(World):
    """The world with a scripted courier: each send_label call takes the next fault."""

    def __init__(self, courier=(), payments=()):
        super().__init__(faults={"refund": list(payments)})
        self.courier = list(courier)
        self.courier_calls = 0

    def send_label(self, order_id, item, key=None):
        self.courier_calls += 1
        fault = self.courier.pop(0) if self.courier else None
        if fault == "TIMEOUT":
            self.tick()
            raise WorldError("TIMEOUT", transient=True)
        if fault == MALFORMED:
            self.tick()
            return {"status": "ok"}          # an answer with no receipt_id
        receipt = super().send_label(order_id, item, key=key)
        if fault == LATE:                    # it landed; the reply did not
            raise WorldError("TIMEOUT", transient=True)
        return receipt


def schedule():
    """Courier slow, payments slow, malformed output once: the combined schedule."""
    return SlowWorld(courier=[LATE, MALFORMED] + ["TIMEOUT"] * 24,
                     payments=["LOST_REPLY"])


def valid_label(out):
    return isinstance(out, dict) and isinstance(out.get("receipt_id"), str)


LAYERS = ("job", "step", "tool")


def nested(fn, budget_for, dep):
    """Wrap fn in the job, step and tool layers. Each layer retries a failure from the
    layer below while the budget it gets allows: BREAK hands every layer call a fresh
    budget of its own; FIX hands every layer the ticket's one shared budget."""
    def wrap(inner, layer):
        def call():
            budget = budget_for(layer)
            while True:
                try:
                    return inner()
                except (WorldError, Exhausted) as e:
                    budget.take(layer, f"{dep} {getattr(e, 'code', 'gave up below')}")
        return call
    for layer in reversed(LAYERS):
        fn = wrap(fn, layer)
    return fn()


def run_break(world, log=print):
    """Three layers, three tries each (two retries per layer), no keys, no breaker."""
    def own(layer):
        return RetryBudget(2, lambda *_: None)

    def label():
        out = world.send_label("2001", "Ceramic mug set")
        if not valid_label(out):
            raise WorldError("MALFORMED")
        return out

    for dep, fn in (("payments", lambda: world.refund("2001", 950)), ("courier", label)):
        try:
            nested(fn, own, dep)
        except Exhausted:
            pass
    log(f"courier calls={world.courier_calls}")
    log(f"labels sent: {len(world.live_labels('2001'))} "
        f"payments: {len(world.payments_for('2001'))}")
    return world


def run_fix(world, retries=3, log=print):
    """One shared budget, a breaker per dependency, keys, validation, escalation."""
    budget = RetryBudget(retries, log)
    breakers = {"payments": Breaker("payments", world, log),
                "courier": Breaker("courier", world, log)}
    done = {}

    def label():
        out = world.send_label("2001", "Ceramic mug set", key="k-T-2001-label")
        if not valid_label(out):
            log("observe malformed tool output -> rejected")
            raise WorldError("MALFORMED")
        return out

    reason, dep = "success", "payments"
    try:
        done["refund"] = nested(lambda: breakers["payments"].call(
            lambda: world.refund("2001", 950, key="k-T-2001-refund")),
            lambda layer: budget, "payments")
        dep = "courier"
        done["label"] = nested(lambda: breakers["courier"].call(label),
                               lambda layer: budget, "courier")
    except (Exhausted, Open):
        reason = f"{dep} unavailable"
        found = world.by_key.get("k-T-2001-label")
        if found:
            log(f"reconcile label by key -> found {found[2]['receipt_id']} (do not resend)")
        log(f"reply escalate: {reason}")
    log(f"courier calls={world.courier_calls}")
    log(f"labels sent: {len(world.live_labels('2001'))} "
        f"payments: {len(world.payments_for('2001'))}")
    return {"world": world, "reason": reason, "budget": budget, "breakers": breakers,
            "done": done}
