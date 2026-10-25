"""Chapter 5: state machines, checkpoints and stop reasons.

MM-100 The Agent as a State Machine: a transition table; an illegal move raises.
MM-101 Checkpoint and Resume: one SQLite transaction per transition, a version on
       every write, and a write carrying an old version is refused (stale).
MM-172 Every Stop Has a Reason: a run ends only in a named stop, with a reply.
"""
import json
import sqlite3

TRANSITIONS = {                       # state -> the states it may move to
    "NEW": {"VERIFYING"},
    "VERIFYING": {"CHOOSING", "ACTING"},
    "CHOOSING": {"ACTING"},
    "ACTING": {"REFUNDED", "DONE"},
    "REFUNDED": {"DONE"},
}
TERMINAL = {"DONE", "HANDOFF", "CANCELLED"}
for s in list(TRANSITIONS):           # any open state may stop for a human or a cancel
    TRANSITIONS[s] |= {"HANDOFF", "CANCELLED"}

STOPS = {   # MM-172: reason -> (terminal state, what the customer is told)
    "success": ("DONE", "Done. Here is what changed: {detail}"),
    "budget_exhausted": ("HANDOFF", "This is taking longer than it should. A person "
                                    "has your ticket and will reply today."),
    "no_progress": ("HANDOFF", "I could not move this forward. A person has your "
                               "ticket and will reply today."),
    "needs_human": ("HANDOFF", "A person needs to look at this. You will hear back today."),
    "cancelled": ("CANCELLED", "Your request is cancelled. Nothing else will change."),
}


class IllegalMove(Exception):
    pass


class StaleWrite(Exception):
    pass


class Store:
    def __init__(self, path=":memory:", transitions=None):
        self.db = sqlite3.connect(path, isolation_level=None)   # we BEGIN ourselves
        self.table = transitions or TRANSITIONS
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS tickets (id TEXT PRIMARY KEY, state TEXT,
                version INTEGER, data TEXT);
            CREATE TABLE IF NOT EXISTS history (id TEXT, version INTEGER, state TEXT,
                observation TEXT);
            CREATE TABLE IF NOT EXISTS stops (id TEXT PRIMARY KEY, reason TEXT,
                reply TEXT, detail TEXT);""")

    def create(self, ticket_id, data=None):
        self.db.execute("BEGIN IMMEDIATE")
        self.db.execute("INSERT INTO tickets VALUES (?, 'NEW', 1, ?)",
                        (ticket_id, json.dumps(data or {})))
        self.db.execute("INSERT INTO history VALUES (?, 1, 'NEW', '')", (ticket_id,))
        self.db.execute("COMMIT")
        return 1

    def load(self, ticket_id):
        state, version, data = self.db.execute(
            "SELECT state, version, data FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
        return state, version, json.loads(data)

    def move(self, ticket_id, to, expected_version, data=None,
             observation=""):
        """One transition = one transaction: legal move,
        current version, or nothing."""
        state, version, old = self.load(ticket_id)
        # checked again inside the UPDATE
        if version != expected_version:
            raise StaleWrite(f"write v={expected_version} "
                             f"but ticket is at v={version}")
        if to not in self.table.get(state, set()):
            raise IllegalMove(f"{state} -> {to} is not in the table")
        try:
            self.db.execute("BEGIN IMMEDIATE")
            cur = self.db.execute(
                "UPDATE tickets SET state = ?, "
                "version = version + 1, data = ? "
                "WHERE id = ? AND version = ?",
                (to, json.dumps({**old, **(data or {})}),
                 ticket_id, expected_version))
            # someone wrote a newer version
            if cur.rowcount == 0:
                raise StaleWrite(f"write v={expected_version} "
                                 f"but ticket is at "
                                 f"v={self.load(ticket_id)[1]}")
            self.db.execute("INSERT INTO history VALUES (?, ?, ?, ?)",
                            (ticket_id, expected_version + 1, to,
                             observation))
            self.db.execute("COMMIT")
        except BaseException:
            self.db.execute("ROLLBACK")
            raise
        return expected_version + 1

    def stop(self, ticket_id, reason, detail=""):
        """MM-172: record why the run stopped and what the customer is told."""
        to, reply = STOPS[reason]
        state, version, _ = self.load(ticket_id)
        if state != to:
            version = self.move(ticket_id, to, version, observation=f"stop {reason}")
        self.db.execute("INSERT OR REPLACE INTO stops VALUES (?, ?, ?, ?)",
                        (ticket_id, reason, reply.format(detail=detail), detail))
        return version

    def stop_record(self, ticket_id):
        row = self.db.execute("SELECT reason, reply, detail FROM stops WHERE id = ?",
                              (ticket_id,)).fetchone()
        return dict(zip(("reason", "reply", "detail"), row)) if row else None

    def history(self, ticket_id):
        return self.db.execute("SELECT version, state, observation FROM history "
                               "WHERE id = ? ORDER BY version", (ticket_id,)).fetchall()


def run_loop(store, ticket_id, propose, act, tr, goal_met, max_steps=8, repeat_limit=3,
             waits=()):
    """A bounded agent loop that always ends in a stop record (MM-172).

    propose(context) -> {"action": ..., "args": ...} or {"final": ...}; act(move) -> text;
    goal_met() reads the world: a final reply counts as success only if it is True.
    A call named in waits is a deliberate wait: the budget bounds it, not the watchdog.
    """
    calls, context, reason, detail, steps = [], f"Ticket {ticket_id}", None, "", 0
    try:
        for steps in range(1, max_steps + 1):
            move = propose(context)
            if not isinstance(move, dict) or not move:
                reason, detail = "needs_human", "model reply was not a valid move"
                break
            if "final" in move:                  # a reply is not proof the goal is met
                reason, detail = (("success", "goal verified in the world") if goal_met()
                                  else ("needs_human", "final reply, goal not met"))
                break
            call = (move.get("action"), json.dumps(move.get("args"), sort_keys=True))
            calls.append(call)
            if call[0] not in waits and calls[-repeat_limit:] == [call] * repeat_limit:
                reason, detail = "no_progress", f"repeated={call[0]} x{repeat_limit}"
                break
            observation = act(move)
            tr.emit("act", f"{call[0]} -> {observation}")
            context += f"\nYou called {call[0]} {call[1]}: {observation}"
        else:
            reason, detail = "budget_exhausted", f"steps={max_steps}/{max_steps}"
    finally:
        if reason is None:                    # a crash still leaves a stop record
            reason, detail = "needs_human", "the run crashed"
        store.stop(ticket_id, reason, detail)
        tr.emit("stop", f"reason={reason} {detail}"
                + (" -> handoff" if STOPS[reason][0] == "HANDOFF" else ""), reason=reason)
    return reason
