"""Chapter 1: the agent harness. Everything around the model, as typed contracts.

MM-171 The Agent Harness: loop, tools, context, state, checks, evals, limits.
MM-094 The Agent Contract: the model PROPOSES; code AUTHORIZES; state RECORDS;
       the tool returns a RECEIPT.
MM-145 The Identity Chain: the customer comes from the session, never the model.
"""
from dataclasses import dataclass, field
from typing import Callable

from events import Trace
from world import WorldError


@dataclass
class Tool:
    name: str
    run: Callable                 # run(world, session, **args) -> dict receipt
    writes: bool = False
    needs_order: bool = True      # carries an order_id that must belong to the caller


@dataclass
class Session:
    customer_id: str              # set by login, never by the model
    tenant_id: str = "a"


@dataclass
class Limits:
    steps: int = 8


# MM-050 recap: the autonomy ladder. Each ticket type gets the least autonomy that works.
RUNGS = {"tracking": "fixed chain", "address change": "agent", "refund": "agent"}

# Which tools the harness offers at each rung, per ticket type.
OFFER = {
    ("address change", "agent"): ["look_up_shipment", "change_address", "ask_carrier"],
    ("address change", "router"): ["look_up_shipment", "change_address"],
    ("refund", "agent"): ["look_up_shipment", "issue_refund"],
    ("tracking", "fixed chain"): ["look_up_shipment"],
}


@dataclass
class Harness:
    model: Callable               # model(context: str, offered: list) -> proposal dict
    tools: dict                   # the registry: name -> Tool
    world: object
    limits: Limits = field(default_factory=Limits)
    rungs: dict = field(default_factory=lambda: dict(RUNGS))
    checks: list = field(default_factory=list)     # verifiers (Chapter 4)
    evals: list = field(default_factory=list)      # eval hooks (Chapters 16-17)
    model_name: str = "stub"

    def authorize(self, proposal, offered, session):
        """MM-094 + MM-145: authorize a proposed action, or refuse."""
        name, args = proposal.get("action"), proposal.get("args") or {}
        if name not in self.tools:
            return False, "not in registry"
        if name not in offered:
            return False, "not offered at this rung"
        if self.tools[name].needs_order:
            order = self.world.order(str(args.get("order_id", "")))
            if order is None:
                return False, "no such order"
            if order["owner"] != session.customer_id:      # identity chain
                return False, "not the caller's order"
        for check in self.checks:
            ok, why = check(proposal, self.world)
            if not ok:
                return False, why
        return True, "authorized"

    def run(self, ticket, ticket_type, session, ticket_id="T-1", echo=True):
        tr = Trace(self.world, ticket_id, session.customer_id, self.model_name,
                   echo=echo)
        state = {"ticket": ticket, "steps": [], "receipts": [], "refused": [],
                 "outcome": None}                       # the state store's record
        tr.emit("harness", f"model={self.model_name} tools={len(self.tools)} "
                f"limits steps={self.limits.steps}")
        rung = self.rungs.get(ticket_type, "person")
        offered = OFFER.get((ticket_type, rung), [])
        tr.emit("route", f"type={ticket_type.replace(' ', '_')} rung={rung.replace(' ', '_')}")
        if rung != "agent":
            return self._fixed(ticket_type, ticket, session, state, tr)
        for _ in range(self.limits.steps):                  # LOOP, bounded by LIMITS
            context = self.context(ticket, state, offered)  # CONTEXT
            proposal = self.model(context, offered)
            if not isinstance(proposal, dict):
                state["outcome"] = "escalate: model reply was not a valid move"
                break
            if "final" in proposal:
                state["outcome"] = str(proposal["final"])
                break
            name = proposal.get("action")
            order = (proposal.get("args") or {}).get("order_id")
            tr.emit("propose", f"{name}" + (f" order={order}" if order else ""),
                    actor="model", proposal=proposal)
            ok, why = self.authorize(proposal, offered, session)
            if order is not None and name in self.tools:
                owner = (self.world.order(str(order)) or {}).get("owner", "none")
                tr.emit("check", f"caller={session.customer_id} order={order} "
                        f"owner={owner} -> {'authorized' if ok else 'refused'}",
                        ok=ok, reason=why)
            elif not ok:
                tr.emit("check", f"{name} -> refused ({why})", ok=False, reason=why)
            state["steps"].append(proposal)
            if not ok:
                state["refused"].append({"proposal": proposal, "reason": why})
                observation = f"refused: {why}"
            else:
                try:
                    receipt = self.tools[name].run(self.world, session,
                                                   **proposal["args"])
                    state["receipts"].append(receipt)                 # STATE records
                    observation = receipt
                    tr.emit("act", f"{name} -> " + (f"receipt {receipt['receipt_id']}"
                                                     if "receipt_id" in receipt else "read"),
                            receipt=receipt)
                except WorldError as e:
                    observation = f"error: {e.code}"
                    tr.emit("act", f"{name} -> error {e.code}")
                except TypeError:              # wrong argument names (Chapter 2 fixes this)
                    observation = f"error: bad arguments for {name}"
                    tr.emit("act", f"{name} -> error bad arguments")
            state["last"] = observation
            tr.emit("observe", show(observation))
        else:
            state["outcome"] = "escalate: step limit reached"
        if state["outcome"] is None:
            state["outcome"] = "escalate: no final reply"
        for hook in self.evals:
            hook(state, self.world)
        tr.emit("reply", state["outcome"])
        state["events"] = tr.events
        return state

    def context(self, ticket, state, offered):
        lines = [f"Ticket: {ticket}", "Tools you may propose: " + ", ".join(offered)]
        for step in state["steps"]:
            lines.append(f"Done: {step.get('action')} {step.get('args')}")
        if "last" in state:
            lines.append(f"Last result: {state['last']}")
        return "\n".join(lines)

    def _fixed(self, ticket_type, ticket, session, state, tr):
        """Rungs 1-2: the code lays the track (Vol 1 Chapter 18)."""
        order_id = "".join(ch for ch in ticket.split("#", 1)[-1][:4] if ch.isdigit())
        status = self.world.shipment(order_id)
        tr.emit("act", f"look_up_shipment {order_id} -> {status}")
        state["steps"].append({"action": "look_up_shipment", "args": {"order_id": order_id}})
        if ticket_type == "address change" and status == "packing":
            receipt = self.world.change_address(order_id, "new address", key=f"adr-{order_id}")
            state["receipts"].append(receipt)
            state["outcome"] = "done: address changed"
        elif ticket_type == "address change":
            state["outcome"] = f"escalate: parcel is {status}; a person must handle it"
        else:
            state["outcome"] = f"answer: #{order_id} is {status}"
        tr.emit("reply", state["outcome"])
        state["events"] = tr.events
        return state


def show(observation):
    if isinstance(observation, dict):
        return " ".join(f"{k}={v}" for k, v in observation.items() if k != "at")
    return str(observation)


# ---- the registry: the only tools that exist --------------------------------
def look_up_shipment(world, session, order_id):
    return {"order_id": order_id, "status": world.shipment(order_id) or "not found"}


def change_address(world, session, order_id, address):
    return world.change_address(order_id, address, key=f"adr-{order_id}-{address}")


def ask_carrier(world, session, order_id):
    return {"order_id": order_id, "redirect": world.ask_carrier(order_id)}


def issue_refund(world, session, order_id):
    """Refunds the order's own amount: the model never supplies money."""
    amount = world.order(order_id)["amount"]
    return world.refund(order_id, amount, key=f"refund-{order_id}")


REGISTRY = {
    "look_up_shipment": Tool("look_up_shipment", look_up_shipment),
    "change_address": Tool("change_address", change_address, writes=True),
    "ask_carrier": Tool("ask_carrier", ask_carrier),
    "issue_refund": Tool("issue_refund", issue_refund, writes=True),
}
