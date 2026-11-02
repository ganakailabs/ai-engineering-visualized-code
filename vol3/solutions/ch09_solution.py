"""Chapter 9 exercise: route a mixed-language ticket.

A Hinglish ticket with two parts and a date limit. Predict the number of parts and
whether the date survives; then check: two parts, manuals then policy, check passes.
On a real model, a rewrite that fails the check must end in a question to the
customer, never a search.

Part 2: three rewrites that change the meaning. Predict whether meaning_kept() catches
each; then check: it misses all three (an action word outside its list, a change of
scope, a negation moved to another product). The lesson: the check is a floor, not a
proof. When a rewrite might have changed scope or who a "not" belongs to, ask the
customer or keep the original message.
"""
import os

import _path  # noqa: F401

import query as Q

MSG = "mera NW-550 charge nahi ho raha, aur kya main 15 November se pehle return kar sakta hoon?"
real = bool(os.environ.get("AIEV_MODEL"))
out = Q.understand(MSG, {})
steps = dict((k, v) for k, v in out if k in ("rewrite", "check", "clarify"))
routes = [v for k, v in out if k == "route"]
if "clarify" in steps:
    assert real, steps                       # the stub's rewrite always passes
    assert not routes, routes
    print(f"check failed {steps.get('check')} -> clarify: {steps['clarify']}")
else:
    assert all(steps["check"].values()), steps
    if not real:
        assert len(steps["rewrite"]) == 2, steps
        assert routes == [(1, "manuals"), (2, "policy")], routes
    for (i, src), part in zip(routes, steps["rewrite"]):
        print(f"part={i} source={src}  {part}")
    print("check " + " ".join(f"{k}=yes" for k in steps["check"]))

LIMITS = [("out-of-vocabulary action", "I want to swap the mug.", ["I want a refund for the mug?"]),
          ("scope change", "Can I return all three mugs?", ["Can I return the mug?"]),
          ("negation binding", "The mug is not broken but the lamp is.",
           ["The lamp is not broken but the mug is?"])]
for name, original, parts in LIMITS:
    kept = Q.meaning_kept(original, parts)
    assert all(kept.values()), (name, kept)            # the check passes: a miss
    print(f"{name}: check passes -> missed (clarify or keep the original)")
print("ch09 solution: OK")
