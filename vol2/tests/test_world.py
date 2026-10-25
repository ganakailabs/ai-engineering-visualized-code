"""Implementation tests for the shared mock world (D2-5)."""
import _path  # noqa: F401

from world import World, WorldError

w = World()
a = w.refund("2001", 950, key="k1")
b = w.refund("2001", 950, key="k1")
assert a["receipt_id"] == b["receipt_id"] and b["replayed"] and len(w.payments) == 1
try:
    w.refund("2001", 9500, key="k1")
    raise AssertionError("a reused key with other args must fail")
except WorldError as e:
    assert e.code == "KEY_REUSED_WITH_OTHER_ARGS"

w = World(faults={"refund": ["LOST_REPLY"]})        # the write lands, the reply is lost
try:
    w.refund("2001", 950, key="k2")
except WorldError as e:
    assert e.transient
assert w.refund("2001", 950, key="k2")["replayed"] and len(w.payments) == 1

w = World(faults={"book_pickup": ["SELL_OUT"]}, stock={"mug set blue": 1})
try:
    w.book_pickup("2001", "mug set blue", key="k3")
except WorldError as e:
    assert e.code == "OUT_OF_STOCK" and w.stock["mug set blue"] == 0
assert w.order("3100")["owner"] == "c-42" and w.order("2001")["owner"] == "asha"
print("test_world: OK")
