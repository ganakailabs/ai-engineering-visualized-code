"""Capstone: the composed path pays once, refuses HUMAN_ONLY, and gates on evidence."""
import _path  # noqa: F401

import capstone

first, again, refused, released = capstone.main()
assert first["state"] == "CONFIRMED" and again["receipt"] == first["receipt"]
assert refused["error"] == "HUMAN_ONLY"
assert released is True
print("test_capstone: OK")
