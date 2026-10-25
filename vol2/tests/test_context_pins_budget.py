"""Ch10 audit: when pins and obligations alone exceed the budget, fit() must
refuse with a clear reason, never silently drop an obligation."""
import _path  # noqa: F401

import context

pins = {"customer": "asha", "order": "2001", "state": "ACTING v=3"}
owed = [f"op-{i:03d} UNKNOWN: reconcile before any new refund" for i in range(40)]
block = context.render_pins(pins, owed)
ctx = context.Context(budget=60, summarize=lambda s, old: s + " folded")
ctx.add("step 1 customer: refund please")
try:
    text, _, _ = ctx.fit(block)
    kept = context.survives(text, pins, owed)[1]
    raise AssertionError(f"fit() returned with {kept}/{len(owed)} obligations")
except context.PinsOverBudget as e:
    print("ok pins over budget ->", e)
