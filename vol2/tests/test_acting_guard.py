"""Ch5 audit: being in VERIFYING is not proof the checks ran. ACTING must be
refused without a recorded passing verification, even though the table allows it."""
import _path  # noqa: F401
import state

s = state.Store()
s.create("T")
v = s.move("T", "VERIFYING", 1)
for bad in (None, {"verification": {"ok": False, "checks": ["owner"]}},
            {"verification": {"ok": True, "checks": []}}):
    try:
        s.move("T", "ACTING", v, data=bad)
        raise AssertionError(f"ACTING without a passing verification: {bad}")
    except state.GuardFailed:
        pass
assert s.load("T")[:2] == ("VERIFYING", 2)
v = s.move("T", "ACTING", v, data={"verification": {"ok": True, "checks": ["owner"]}})
assert s.load("T")[:2] == ("ACTING", 3)
print("ok acting guard")
