"""Ch9 audit: expiry must affect reads before cleanup runs."""
import _path  # noqa: F401

from memory import Memory
from world import World

w = World()
m = Memory(w)
m.write("asha", "call_window", "after 6pm", "session", "customer", "preference",
        "chat", hours=1)
assert m.recall("asha")["facts"], "visible while live"
w.tick(120)                                   # past expiry; expire() NOT run
got = m.recall("asha")
assert not got["facts"], got["facts"]
assert "after 6pm" not in got["summary"], got["summary"]
print("ok memory expiry at read time")
