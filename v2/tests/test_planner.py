"""Implementation tests for Chapter 3: the plan checker and plan repair."""
import copy

import _path  # noqa: F401

import ch03
import planner

good = ch03.first_plan()
assert planner.check_plan(copy.deepcopy(good)) == []


def broken(edit):
    plan = copy.deepcopy(good)
    edit(plan["steps"])
    return planner.check_plan(plan)


assert "unknown tool" in broken(lambda s: s[0].update(tool="refund_all"))[0]
assert "takes" in broken(lambda s: s[1].update(args={"sku": "blue"}))[0]
assert "must be one of" in broken(lambda s: s[2].update(args={"item": "mug set red"}))[0]
assert "order_id" in broken(lambda s: s[0].update(args={"order_id": "two"}))[0]
assert "unknown step" in broken(lambda s: s[1].update(after=["n9"]))[0]
assert "cycle" in broken(lambda s: s[0].update(after=["n5"]))[0]
assert "exactly one reply" in broken(lambda s: s.pop())[0]
assert "wait for every" in broken(lambda s: s[5].update(after=["n1"]))[0]
def second_choice(s):
    s.insert(3, dict(s[2], id="n3x"))
    s[4]["after"].append("n3x")


assert "exactly one choose" in broken(second_choice)[0]
assert "not the chosen item" in broken(
    lambda s: s[3].update(args={"order_id": "2001", "item": "mug set green"}))[0]
assert planner.check_plan({"steps": "do it"}) == ["plan must be a list of 1-10 steps"]

# repair keeps VERIFY ORDER, voids the blue label, and leaves one live label
w = ch03.swap_world()
r = ch03.handle(w, echo=False)
repair = r["trace"].of("plan")[-1]["payload"]
assert r["status"] == "done" and repair["kept"] == ["n1"]
assert {"n2", "n3", "n4", "n5", "n6"} <= set(repair["invalid"])
assert [lab["item"] for lab in w.live_labels("2001")] == ["mug set green"]
assert [lab["status"] for lab in w.labels] == ["void", "live"]
assert len(w.write_calls("verify_order")) == 0 and len(w.pickups) == 1

# BREAK strip "Replan Undid Finished Work": two live labels (documented failure)
w = ch03.swap_world()
ch03.handle(w, naive=True, echo=False)
assert len(w.live_labels("2001")) == 2

# keys as the backstop: a full replan with stable keys cannot resend the same label
w = ch03.swap_world({"book_pickup": ["COURIER_UNAVAILABLE"]})
ch03.handle(w, naive=True, echo=False)
assert len(w.write_calls("send_label")) == 2            # fresh keys: sent twice
w = ch03.swap_world({"book_pickup": ["COURIER_UNAVAILABLE"]})
ch03.handle(w, naive=True, fresh_keys=False, echo=False)
assert len(w.write_calls("send_label")) == 1 and len(w.live_labels("2001")) == 1
print("test_planner: OK")
