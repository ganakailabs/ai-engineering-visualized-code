"""Chapter 7: long-running tickets. Waits, status events and cancellation.

MM-157 The Waiting Ticket: a waiting state ends by an event or a timeout. Both are
       legal moves; the first to commit its state version wins, and the other is
       recorded as stale. Timers live in the database, so a restart re-arms them.
MM-158 Status Is an Event: every transition writes a status the customer can see; a
       cancel is an event too, and what it means depends on the state it meets.

State before effect, effect before status: the winning courier reply moves the ticket
to LABEL_PENDING (the intent, with the label's key), the label is sent under that key,
and only a confirmed receipt moves it to LABEL_SENT. A crash or a failed call between
the two leaves LABEL_PENDING, which resume() completes with the same key. A timer is
marked fired only after its delivery has run, so an interrupted delivery stays due.
"""
from datetime import timedelta

import state
from world import WorldError

TABLE = {s: set(t) for s, t in state.TRANSITIONS.items()}
TABLE["ACTING"] |= {"WAITING_COURIER"}
TABLE["WAITING_COURIER"] = {"LABEL_PENDING", "HANDOFF", "CANCELLED"}
TABLE["LABEL_PENDING"] = {"LABEL_SENT", "HANDOFF", "CANCELLED"}
TABLE["LABEL_SENT"] = {"DONE", "HANDOFF", "CANCELLED"}

STATUS = {"NEW": "received", "VERIFYING": "checking", "CHOOSING": "checking",
          "ACTING": "checking", "WAITING_COURIER": "waiting_for_courier",
          "LABEL_PENDING": "label_pending",
          "LABEL_SENT": "label_sent", "REFUNDED": "refunded", "DONE": "done",
          "HANDOFF": "with_a_person", "CANCELLED": "cancelled"}

# What "cancel" means in each state (MM-158). Irreversible steps change the answer.
CANCEL = {"NEW": "cancel", "VERIFYING": "cancel", "CHOOSING": "cancel",
          "ACTING": "cancel", "WAITING_COURIER": "cancel",
          "LABEL_PENDING": "compensate",       # the send may be in flight: void any label
          "LABEL_SENT": "compensate",          # void the label first: a new action
          "REFUNDED": "refuse",                # money has moved: a person reconciles
          "DONE": "refuse", "HANDOFF": "refuse", "CANCELLED": "refuse"}


CHECKED = {"verification": {"ok": True, "checks": ["owner", "damage photo"]}}


class Waits:
    def __init__(self, store, world, tr):
        self.store, self.world, self.tr = store, world, tr
        store.db.execute("CREATE TABLE IF NOT EXISTS timers (ticket TEXT, fire_at TEXT, "
                         "armed_v INTEGER, fired INTEGER DEFAULT 0)")
        store.db.execute("CREATE TABLE IF NOT EXISTS status (ticket TEXT, v INTEGER, "
                         "status TEXT, at TEXT)")

    def move(self, ticket, to, version, why="", data=None):
        """A transition and its status event, written together."""
        v = self.store.move(ticket, to, version, data=data, observation=why, also=[(
            "INSERT INTO status VALUES (?, ?, ?, ?)",
            (ticket, version + 1, STATUS[to], self.world.now()))])
        self.tr.emit("state", f"{to} v={v} status={STATUS[to]}", state_to=to,
                     state_version=v)
        return v

    def wait(self, ticket, version, days):
        """Park the ticket and arm a durable timer at the version it was parked at."""
        v = self.move(ticket, "WAITING_COURIER", version, "asked the courier for a slot")
        fire_at = (self.world.clock + timedelta(days=days)).isoformat()
        self.store.db.execute("INSERT INTO timers (ticket, fire_at, armed_v) VALUES "
                              "(?, ?, ?)", (ticket, fire_at, v))
        return v

    def deliver(self, ticket, event, seen_v, check_version=True):
        """courier_reply or timeout tries its one legal transition."""
        to = {"courier_reply": "LABEL_PENDING",
              "timeout": "HANDOFF"}[event]
        if not check_version:                  # BREAK: obey whatever arrives
            current, seen_v, _ = self.store.load(ticket)
            self.store.table = {**self.store.table, current: self.store.table.get(
                current, set()) | {to}}
        try:
            v = self.move(ticket, to, seen_v, event)
        except (state.StaleWrite, state.IllegalMove) as e:
            self.tr.emit("observe", f"event {event} v={seen_v} "
                         f"-> ignored, stale ({e})")
            return None
        if event == "courier_reply":
            self.resume(ticket, quiet_ok=True)
            return self.store.load(ticket)[1]          # the ticket's version now
        # The timeout hands the ticket to a person. What the person does next is a
        # separate (simulated) event, recorded as theirs, not the agent's.
        self.tr.emit("handoff", "timeout: ticket handed to a person")
        label = self.world.send_label(
            "2001", "mug set green", key=f"k-{ticket}-person-label")
        self.tr.emit("observe", f"simulated person event: label {label['receipt_id']} "
                     "sent by a person", actor="human")
        return v

    def resume(self, ticket, quiet_ok=False):
        """Complete a LABEL_PENDING ticket: send under the intent's key, then confirm.
        Safe to repeat: the key makes the send idempotent at the receiver."""
        current, v, _ = self.store.load(ticket)
        if current != "LABEL_PENDING":
            return current
        pending_v = [hv for hv, st, _ in self.store.history(ticket)
                     if st == "LABEL_PENDING"][-1]
        try:
            label = self.world.send_label(
                "2001", "mug set green", key=f"k-{ticket}-label-v{pending_v}")
        except WorldError as e:
            self.tr.emit("observe", f"send_label -> {e.code}; ticket stays LABEL_PENDING")
            return None if quiet_ok else current
        self.tr.emit("act", f"send_label -> {label['receipt_id']}")
        self.move(ticket, "LABEL_SENT", v, f"label {label['receipt_id']} confirmed")
        return "LABEL_SENT"

    def fire_due(self):
        """Wake every due timer from the database (also after a restart)."""
        due = self.store.db.execute(
            "SELECT rowid, ticket, armed_v FROM timers WHERE fired = 0 AND fire_at <= ?",
            (self.world.clock.isoformat(),)).fetchall()
        for rowid, ticket, armed_v in due:
            self.deliver(ticket, "timeout", armed_v)       # stale on a repeat: harmless
            self.store.db.execute("UPDATE timers SET fired = 1 WHERE rowid = ?", (rowid,))
        return len(due)

    def cancel(self, ticket):
        """A cancel is an event; its meaning comes from the state it meets."""
        current, v, _ = self.store.load(ticket)
        rule = CANCEL[current]
        if rule == "refuse":
            why = {"REFUNDED": "refund already paid; a person reconciles it"}.get(
                current, f"ticket is {current}")
            self.tr.emit("check", f"cancel at {current} -> refused ({why})")
            return current, why
        if rule == "compensate":
            for lab in self.world.live_labels("2001"):
                r = self.world.void_label(lab["receipt_id"], key=f"k-{ticket}-void")
                self.tr.emit("act", f"void_label {lab['receipt_id']} -> {r['receipt_id']}")
        self.move(ticket, "CANCELLED", v, "customer cancelled")
        return "CANCELLED", rule

    def statuses(self, ticket):
        """What the customer sees: each status once, in order."""
        seen = []
        for (s,) in self.store.db.execute(
                "SELECT status FROM status WHERE ticket = ? ORDER BY v", (ticket,)):
            if not seen or seen[-1] != s:
                seen.append(s)
        return seen


def start_swap(store, world, tr, ticket="T-2001-w", days=3):
    """Drive the swap ticket to WAITING_COURIER; return (waits, version)."""
    w = Waits(store, world, tr)
    store.create(ticket)
    store.db.execute("INSERT INTO status VALUES (?, 1, 'received', ?)", (ticket, world.now()))
    v, echo, tr.echo = 1, tr.echo, False          # the earlier moves, not printed
    for to in ("VERIFYING", "CHOOSING", "ACTING"):
        v = w.move(ticket, to, v, data=CHECKED if to == "ACTING" else None)
    tr.echo = echo
    return w, w.wait(ticket, v, days)

