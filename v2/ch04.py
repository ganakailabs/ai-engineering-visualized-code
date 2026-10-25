"""Chapter 4: Verification Before Commit: Checks, Bounded Revision and Postconditions.

Run from the support-assistant folder:  python3 v2/ch04.py
Real model (optional):  AIEV_MODEL=ollama:llama3.2 python3 v2/ch04.py
Parts 1-3 ask the model (the stub is a script, a demonstration); part 4 is scripted.
"""
import llm
import verify
from events import Trace
from harness import Session
from world import World

ASHA = Session("asha")
SYSTEM = ("You decide one Northwind Goods refund request. Policy:\n" + verify.POLICY_TEXT +
          '\nReply with ONE JSON object and nothing else: {"decision": "approve" or '
          '"deny" or "hold", "rule": "<the clause id you applied, e.g. R2>", '
          '"reply": "<one sentence to the customer>"}')
REFLECT = ("You wrote the draft decision below. Are you sure? Check it against the policy "
           "and reply with the final decision as the same JSON object.")


def stub(user):
    """Scripted (a demonstration, not a model): agrees with itself; obeys a failed check."""
    if "Check failed: rule R3" in user:
        return {"decision": "deny", "rule": "R3", "reply": "Final-sale items cannot be refunded."}
    if "#2001" in user:
        return {"decision": "approve", "rule": "R2", "reply": "Refund approved."}
    return {"decision": "approve", "rule": "R1", "reply": "Refund approved."}


def ask_model(user):
    return llm.ask_json(SYSTEM, user, stub)[0]


def reflect(user, draft):
    """Same-model reflection: the model reviews its own draft and answers again."""
    return llm.ask_json(SYSTEM, f"{user}\nYour draft: {draft}\n{REFLECT}",
                        lambda u: draft)[0]


def stubborn(user):
    """Scripted model that approves #4410 every time, whatever the check says."""
    return {"decision": "approve", "rule": "R1", "reply": "Approved."}


def run(order_id, ask, verifier=True, faults=None, title="", ticket="T-4410-a",
        reflect=None):
    print(f"--- {title} ---")
    world = World(faults=faults)
    tr = Trace(world, ticket, "asha", llm.name())
    result = verify.decide(world, ASHA, order_id, ask, tr, verifier=verifier,
                           key=f"k-{ticket}-refund-{order_id}", reflect=reflect)
    print(f"world: payments for #{order_id}={len(world.payments_for(order_id))} "
          f"status={result['status']}")
    return world, result, tr


if __name__ == "__main__":
    print(f"model={llm.name()}")
    run("4410", ask_model, title="1. #4410 final sale, verifier on (FIX)")
    run("4410", ask_model, verifier=False, reflect=reflect,
        title="2. #4410, same-model reflection only (BREAK)")
    run("2001", ask_model, title="3a. #2001 damaged mug set: write, then read back",
        ticket="T-2001-a")
    run("2001", ask_model, faults={"refund": ["GHOST"]}, ticket="T-2001-a",
        title="3b. #2001, the tool reports a payment it never made (scripted fault)")
    run("4410", stubborn, title="4. a scripted model that never revises")
