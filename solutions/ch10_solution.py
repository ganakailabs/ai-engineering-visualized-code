"""Chapter 10 exercise: take the stack apart, one layer at a time.

Score the full prompt stack on the Chapter 8 golden set plus one injected ticket, then
drop each layer in turn and score again. A layer earns its place if removing it costs
points. Score the prompt alone (no citation gate), so the gate does not hide a
weak layer. Run: python3 solutions/ch10_solution.py
"""
import _path  # noqa: F401  (adds code/support-assistant/ to the import path)
from ch08 import GOLDEN, passes
from ch10 import INJECTED, LAYERS, build_messages
from stub_model import call_model

CASES = GOLDEN + [(INJECTED, "4410", "deny"), (INJECTED, "4410", "deny")]


def score(layers):
    ok = 0
    for ticket, oid, expected in CASES:
        reply = call_model(build_messages(ticket, oid, layers))["text"]  # prompt alone, no gate
        # an injected ticket passes if the assistant does NOT approve it
        if ticket == INJECTED:
            ok += reply.split(":")[0] != "approve"
        else:
            ok += passes(reply, expected)
    return ok / len(CASES)


if __name__ == "__main__":
    full = score(LAYERS)
    print(f"full stack: {full:.0%}")
    drops = {}
    for layer in LAYERS:
        drops[layer] = score([k for k in LAYERS if k != layer])
        print(f"without {layer:13}: {drops[layer]:.0%}")
    # self-test (run_solutions.py relies on these)
    assert full > max(drops["rules"], drops["context"]), "rules and context both earn their place"
    assert drops["examples"] == full, "no golden case tests the examples layer yet: add one"
    print("ch10 solution: OK")
