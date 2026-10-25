"""Chapter 10: context engineering for long-running agents.

MM-104 The Growing Context: every step adds history, so each model call is assembled
       under a token budget. When it is over budget, old turns are compacted into a
       summary. Pins (who, which order, which state) and open obligations (ledger rows
       still UNKNOWN, pending approvals) are NOT trusted to the summary: they are
       projected from durable state on every call, and a survival check proves it.
MM-105 Just-in-Time Context: a manual section is loaded at the step that needs it,
       not packed up front for all thirty steps.

Token counts use Vol 1's PLACEHOLDER counter (one token per word or punctuation mark);
real tokenizers differ, so measure with your provider's tokenizer.
"""
import _root  # noqa: F401  (Vol 1 stub_model.py, store.py)

from stub_model import rough_token_count as count
from store import HANDBOOK

OPEN = {"UNKNOWN", "NEEDS_HUMAN"}          # ledger states that are still owed


class PinsOverBudget(Exception):
    """The non-droppable part alone does not fit: split the task or stop."""


def project(session, store, book, ticket_id, op_ids=(), approvals=()):
    """Rebuild pins and obligations from durable state.
    Never from history."""
    state, version, data = store.load(ticket_id)
    # identity from the session, order from the ticket record,
    # state from the state machine
    pins = {"customer": session["customer_id"],
            "order": data["order_id"],
            "state": f"{state} v={version}"}
    owed = []
    for op in op_ids:  # the action ledger
        row = book.row(op)
        if row and row["state"] in OPEN:
            owed.append(f"{op} {row['state']}: "
                        "reconcile before any new refund")
    owed += [f"approval {a} pending" for a in approvals]
    return pins, owed


def render_pins(pins, owed):
    lines = ["PINNED (rebuilt from state on every call):"]
    lines += [f"- {k}: {v}" for k, v in pins.items()]
    lines += ["OPEN OBLIGATIONS:"] + [f"- {o}" for o in owed or ["none"]]
    return "\n".join(lines)


def survives(text, pins, owed):
    """The survival check: every pin value and every obligation is in the call."""
    kept_pins = sum(str(v) in text for v in pins.values())
    kept_owed = sum(o.split()[0] in text for o in owed)
    return kept_pins, kept_owed


class Context:
    """History plus a summary, assembled under a budget for each model call."""

    def __init__(self, budget, summarize, keep_recent=4, pinned=True):
        self.budget, self.summarize = budget, summarize
        self.keep_recent, self.pinned = keep_recent, pinned
        self.turns, self.summary, self.loaded = [], "", {}

    def add(self, turn):
        self.turns.append(turn)

    def load(self, section):
        """MM-105: one manual section, at the step that needs it."""
        self.loaded[section] = HANDBOOK[section]

    def unload(self):
        self.loaded = {}

    def assemble(self, pin_block=""):
        parts = []
        if self.pinned and pin_block:
            parts.append(pin_block)
        if self.summary:
            parts.append("SUMMARY OF EARLIER STEPS: " + self.summary)
        parts += [f"MANUAL {k}: {v}" for k, v in self.loaded.items()]
        parts += ["RECENT:"] + self.turns
        return "\n".join(parts)

    def compact(self, keep=None):
        """Fold all but the most recent turns into the summary. Returns turns folded."""
        keep = self.keep_recent if keep is None else keep
        old, self.turns = self.turns[:-keep], self.turns[-keep:]
        if old:
            self.summary = self.summarize(self.summary, old)
        return len(old)

    def fit(self, pin_block=""):
        """Assemble under the budget. Returns (text, tokens, folded).

        Over budget: fold old turns into the summary; still over, keep fewer recent
        turns; still over, cut the summary (the only lossy part: pins are rebuilt)."""
        if pin_block and self.pinned and count(pin_block) > self.budget:
            raise PinsOverBudget(f"pins need {count(pin_block)} tokens, "
                                 f"budget is {self.budget}")   # never trim them
        text, folded = self.assemble(pin_block), 0
        keep = self.keep_recent
        while count(text) > self.budget and keep >= 1:
            folded += self.compact(keep)
            text, keep = self.assemble(pin_block), keep - 1
        words = self.summary.split()
        while count(text) > self.budget and words:
            words = words[:-1]
            self.summary = " ".join(words) + (" ..." if words else "")
            text = self.assemble(pin_block)
        return text, count(text), folded


def up_front_tokens():
    """What packing the whole manual into every call would cost (for comparison)."""
    return count("\n".join(f"MANUAL {k}: {v}" for k, v in HANDBOOK.items()))
