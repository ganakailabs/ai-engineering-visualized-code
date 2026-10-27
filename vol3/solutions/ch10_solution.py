"""Chapter 10 exercise: out-rank the newer ticket.

Add a past ticket from today that contradicts the effective policy. Predict which source
is cited; then check: the policy wins on authority and is the only clause cited.
"""
import _path  # noqa: F401

import precedence as P

P.CLAUSES["ticket-9001"] = dict(P.CLAUSES["ticket-8812"], published=P.TODAY, ingested=P.TODAY,
                                effective_from=P.TODAY, text="Agent: returns are 45 days now.")
kept, dropped, esc = P.precedence(["R1@2026-09-15", "ticket-9001"])
assert kept == ["R1@2026-09-15"] and dropped == [("ticket-9001", "authority")] and not esc
print(f"precedence kept={kept[0]} dropped=ticket-9001 reason=authority")
print("cite " + P.cite(kept[0]))
print("ch10 solution: OK")
