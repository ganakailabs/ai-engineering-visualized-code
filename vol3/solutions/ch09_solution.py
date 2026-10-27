"""Chapter 9 exercise: route a mixed-language ticket.

A Hinglish ticket with two parts and a date limit. Predict the number of parts and
whether the date survives; then check: two parts, manuals then policy, check passes.
"""
import _path  # noqa: F401

import query as Q

MSG = "mera NW-550 charge nahi ho raha, aur kya main 15 November se pehle return kar sakta hoon?"
steps = dict((k, v) for k, v in Q.understand(MSG, {}) if k in ("rewrite", "check"))
routes = [v for k, v in Q.understand(MSG, {}) if k == "route"]
assert len(steps["rewrite"]) == 2 and all(steps["check"].values()), steps
assert routes == [(1, "manuals"), (2, "policy")], routes
for (i, src), part in zip(routes, steps["rewrite"]):
    print(f"part={i} source={src}  {part}")
print("check " + " ".join(f"{k}=yes" for k in steps["check"]))
print("ch09 solution: OK")
