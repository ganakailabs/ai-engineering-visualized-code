"""vol3-start: Vol 2's final assistant runs unchanged from vol3/."""
import _path  # noqa: F401

import start
from store import HANDBOOK

r = start.run(echo=False)
assert r["reason"] == "success", r["reason"]
assert set(r["cites"]) <= set(HANDBOOK) and "R2" in r["cites"], r["cites"]
assert len(HANDBOOK) == 9
print("test_start: OK")
