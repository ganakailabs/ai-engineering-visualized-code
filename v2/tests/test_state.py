"""Implementation tests for Chapter 5: legal moves, versions, crash and resume."""
import _path  # noqa: F401

import ch05
import state

store = ch05.impossible_jump()                       # FIX: the table refuses it
assert store.load("T-4410-a")[:2] == ("NEW", 1)
assert ch05.impossible_jump(use_table=False).load("T-4410-a")[0] == "REFUNDED"  # BREAK

store = ch05.crash_and_resume()                      # crash after CHOOSING, resume
states = [s for _, s, _ in store.history("T-2001-s")]
assert states == ["NEW", "VERIFYING", "CHOOSING", "ACTING", "DONE"], states
assert store.load("T-2001-s")[:2] == ("DONE", 5)     # worker2's v=3 write changed nothing

s = state.Store()
s.create("T")
v = s.move("T", "VERIFYING", 1)
for bad in (lambda: s.move("T", "ACTING", 1), lambda: s.move("T", "DONE", v)):
    try:
        bad()
        raise AssertionError("must raise")
    except (state.StaleWrite, state.IllegalMove):
        pass
assert s.load("T")[:2] == ("VERIFYING", 2)
print("test_state: OK")
