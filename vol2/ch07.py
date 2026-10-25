"""Chapter 7: Long-Running Tickets: Waits, Progress and Cancellation.

Run from the repo root:  python3 vol2/ch07.py
Real model (optional):  AIEV_MODEL=ollama:llama3.2 python3 vol2/ch07.py
Parts 1-4 are scripted event orders on the simulated clock (demonstrations). In part 5
the model reads the customer's message; the cancel rules decide what it means.
"""
import os
import tempfile

import llm
import state
import waits
from events import Trace
from world import World

T = "T-2001-w"


def setup(path=":memory:"):
    world = World()
    tr = Trace(world, T, "asha", llm.name())
    store = state.Store(path, transitions=waits.TABLE)
    w, v = waits.start_swap(store, world, tr, T)
    return world, store, w, v


def courier_answers():
    print("--- 1. the courier answers in two days, twice (scripted) ---")
    world, store, w, armed = setup()
    world.tick(2 * 24 * 60)
    w.tr.emit("observe", "clock +2 days")
    v = w.deliver(T, "courier_reply", armed)
    w.deliver(T, "courier_reply", armed)            # the same reply, delivered again
    w.move(T, "DONE", v)
    store.stop(T, "success", "label sent")
    w.tr.emit("stop", "reason=success", reason="success")
    return world, store, w


def late_courier(check_version):
    print(f"--- 2. the courier answers after the timeout "
          f"({'FIX: version check' if check_version else 'BREAK: no version check'}) ---")
    world, store, w, armed = setup()
    world.tick(3 * 24 * 60)
    w.tr.emit("observe", "clock +3 days; the timer is due")
    w.fire_due()
    world.tick(24 * 60)
    w.tr.emit("observe", "clock +1 day; the courier finally answers")
    w.deliver(T, "courier_reply", armed, check_version=check_version)
    w.tr.emit("observe", f"live labels for #2001: {len(world.live_labels('2001'))}")
    return world, store


def lost_wakeup():
    print("--- 3. the process is down when the timer is due (scripted) ---")
    path = os.path.join(tempfile.mkdtemp(), "tickets.db")
    world, store, w, armed = setup(path)
    world.tick(4 * 24 * 60)                         # nothing runs for four days
    w.tr.emit("observe", "process down; clock +4 days")
    again = waits.Waits(state.Store(path, transitions=waits.TABLE), world, w.tr)
    due = again.store.db.execute("SELECT COUNT(*) FROM timers WHERE fired = 0").fetchone()[0]
    w.tr.emit("resume", f"restart: {due} unfired timer read from the database")
    again.fire_due()
    return world, again.store


def cancels():
    print("--- 4. cancel means different things in different states (scripted) ---")
    out = {}
    world, store, w, armed = setup()
    out["waiting"] = w.cancel(T)
    store.stop(T, "cancelled")
    w.tr.emit("stop", "reason=cancelled", reason="cancelled")
    world, store, w, armed = setup()
    w.deliver(T, "courier_reply", armed)
    out["label_sent"] = w.cancel(T)
    out["labels_after_void"] = len(world.live_labels("2001"))
    world = World()
    tr = Trace(world, "T-2001-r", "asha")
    store = state.Store(transitions=waits.TABLE)
    w = waits.Waits(store, world, tr)
    store.create("T-2001-r")
    v, tr.echo = 1, False
    for to in ("VERIFYING", "ACTING", "REFUNDED"):
        v = w.move("T-2001-r", to, v,
                   data=waits.CHECKED if to == "ACTING" else None)
    tr.echo = True
    tr.emit("state", f"REFUNDED v={v} (refund ticket)")
    world.refund("2001", 950, key="k-T-2001-r-refund")
    out["refunded"] = w.cancel("T-2001-r")
    store.stop("T-2001-r", "needs_human", "cancel after refund")
    tr.emit("stop", "reason=needs_human", reason="needs_human")
    out["payments"] = len(world.payments_for("2001"))
    return out


SYSTEM = ("You read one customer message about an open Northwind Goods ticket. Reply "
          'with ONE JSON object and nothing else: {"intent": "cancel" or "status" or '
          '"other"}')


def stub(user):
    return {"intent": "cancel" if "cancel" in user.lower() else "status"}


def customer_writes(message):
    """The model classifies; the state table and the cancel rules decide."""
    print(f"--- 5. the customer writes (model={llm.name()}): {message!r} ---")
    world, store, w, armed = setup()
    w.deliver(T, "courier_reply", armed)            # the label is already out
    move, _ = llm.ask_json(SYSTEM, f"Message: {message}", stub)
    intent = (move or {}).get("intent", "other")
    w.tr.emit("decide", f"intent={intent}", actor="model")
    if intent == "cancel":
        w.cancel(T)
    w.tr.emit("reply", "status: " + " > ".join(w.statuses(T)))
    return world, store, intent


if __name__ == "__main__":
    courier_answers()
    late_courier(False)
    late_courier(True)
    lost_wakeup()
    cancels()
    customer_writes("Where is my swap? It has been two days.")
    customer_writes("Please cancel the swap, I will keep the cracked set.")
