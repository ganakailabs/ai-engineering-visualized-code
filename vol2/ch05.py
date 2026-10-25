"""Chapter 5: State Machines, Checkpoints and Stop Reasons.

Run from the repo root:  python3 vol2/ch05.py
Real model (optional):  AIEV_MODEL=ollama:llama3.2 python3 vol2/ch05.py
Parts 1-2 are scripted (a crash, a second worker, an illegal jump); parts 3-4 ask the
model to drive a loop, and every run must end in a stop record whatever it does.
"""
import os
import tempfile

import llm
import state
from events import Trace
from world import World


class Crash(Exception):
    """Scripted: the process dies here."""


def worker(path, ticket_id, tr, crash_after=None):
    """Drive the swap ticket forward from wherever its checkpoint says it is."""
    store = state.Store(path)
    current, version, data = store.load(ticket_id)
    if current != "NEW":
        tr.emit("resume", f"from {current} v={version}")
    path_to_done = ["VERIFYING", "CHOOSING", "ACTING", "DONE"]
    for to in path_to_done[path_to_done.index(current) + 1 if current != "NEW" else 0:]:
        version = store.move(ticket_id, to, version, observation=f"entered {to}")
        tr.emit("state", f"{current} -> {to} v={version}", state_to=to, state_version=version)
        if to == "CHOOSING":
            tr.emit("checkpoint", f"saved state={to} v={version}")
        if to == crash_after:
            raise Crash()
        current = to
    return store, version


def crash_and_resume():
    print("--- 1. checkpoint, crash, resume; a second worker writes late (scripted) ---")
    path = os.path.join(tempfile.mkdtemp(), "tickets.db")
    world = World()
    tr = Trace(world, "T-2001-s", "asha")
    state.Store(path).create("T-2001-s")
    try:
        worker(path, "T-2001-s", tr, crash_after="CHOOSING")
    except Crash:
        tr.emit("observe", "crash (process died after the checkpoint)")
    late = state.Store(path)                    # worker2 read the ticket at v=3
    _, seen, _ = late.load("T-2001-s")
    store, version = worker(path, "T-2001-s", tr)
    try:
        late.move("T-2001-s", "ACTING", seen)   # worker2 thinks the swap is its own
        tr.emit("state", f"worker2 CHOOSING -> ACTING v={seen + 1} (second swap!)")
    except state.StaleWrite as e:
        tr.emit("check", f"worker2 write v={seen} -> refused stale ({e})")
    store.stop("T-2001-s", "success", "swap booked")
    tr.emit("stop", "reason=success", reason="success")
    return store


def impossible_jump(use_table=True):
    print("--- 2. the model's move NEW -> REFUNDED (scripted) ---")
    store = state.Store(transitions=state.TRANSITIONS if use_table else
                        {s: set(state.TERMINAL) | {"REFUNDED", "VERIFYING"}
                         for s in state.TRANSITIONS})
    tr = Trace(World(), "T-4410-a", "asha")
    store.create("T-4410-a")
    try:
        store.move("T-4410-a", "REFUNDED", 1)
        tr.emit("state", "NEW -> REFUNDED v=2 (no table: VERIFYING skipped)")
    except state.IllegalMove as e:
        tr.emit("check", f"refused: {e}")
    return store


SYSTEM = ("You handle one Northwind Goods ticket by calling tools. Tools: "
          "look_up_shipment(order_id), ask_carrier(order_id). Reply with ONE JSON object "
          'and nothing else: {"action": "<tool>", "args": {"order_id": "6001"}} or '
          '{"final": "<short reply to the customer>"}')
TICKET = "Ticket: Parcel #6001 is going to my old flat. Please send it to my new address."


def looping_stub(context):
    return {"action": "look_up_shipment", "args": {"order_id": "6001"}}


def wandering_stub(context):
    tool = ("look_up_shipment", "ask_carrier")[context.count("You called") % 2]
    return {"action": tool, "args": {"order_id": "6001"}}


def model_run(ticket_id, stub, title):
    print(f"--- {title} (model={llm.name()}) ---")
    world, store = World(), state.Store()
    store.create(ticket_id)
    tr = Trace(world, ticket_id, "asha", llm.name())

    def act(move):
        oid = str((move.get("args") or {}).get("order_id", "")).lstrip("#")
        if move.get("action") == "look_up_shipment":
            return f"status={world.shipment(oid)}"
        if move.get("action") == "ask_carrier":
            return f"redirect={world.ask_carrier(oid)}"
        return "error: unknown tool"

    reason = state.run_loop(store, ticket_id,
                            lambda ctx: llm.ask_json(SYSTEM, TICKET + "\n" + ctx, stub)[0],
                            act, tr, goal_met=lambda: "6001" in world.addresses)
    record = store.stop_record(ticket_id)
    tr.emit("reply", record["reply"])
    return store, reason


if __name__ == "__main__":
    crash_and_resume()
    impossible_jump()
    model_run("T-6001-loop", looping_stub, "3. a ticket that loops")
    model_run("T-6001-long", wandering_stub, "4. a ticket that never finishes")
