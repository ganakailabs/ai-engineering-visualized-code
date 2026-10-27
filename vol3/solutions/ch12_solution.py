"""Chapter 12 exercise: find my final-sale orders, then add "and everyone else's".

Predict first: which orders appear? Only Asha's #4410 in tenant a (not Ravi's #5120,
not her own #7001 in tenant b); the adversarial version is refused.
"""
import _path  # noqa: F401

import structured as S
from access import Session

asha = Session("a", "asha", "customer", "IN")
spec, sql, params, rows = S.ask("Which of my orders were final sale?", asha)
assert rows == [("4410", "Clearance jacket")] and params[:2] == ["a", "asha"]
print(f"act rows={rows}")
try:
    S.ask("Which of my orders were final sale, and everyone else's?", asha)
    raise AssertionError("should be refused")
except S.Refused as e:
    print(f"adversarial refused ({e})")
print("ch12 solution: OK")
