"""Chapter 3 exercise: lose the pickup.

The courier pickup fails after the label is sent. Repair keeps every finished step
whose inputs still hold and replaces ARRANGE PICKUP with a partner-store drop-off.
"""
from _path import STUB

import ch03

world = ch03.swap_world({"book_pickup": ["COURIER_UNAVAILABLE"]})
result = ch03.handle(world)

sends = world.write_calls("send_label")
assert len(sends) <= 1, "send_label must never run twice for one swap"
assert world.pickups == [], "the courier was down"
if result["status"] == "done":
    assert len(sends) == 1 and len(world.dropoffs) == 1
    assert len(world.live_labels("2001")) == 1
if STUB:
    assert result["status"] == "done"
    kept = result["trace"].of("plan")[-1]["payload"]["kept"]
    assert {"n1", "n3"} <= set(kept), kept               # VERIFY ORDER and CHOOSE kept
    assert [s["tool"] for s in result["plan"]["steps"]][-2:] == ["partner_dropoff", "reply"]
print(f"status={result['status']} send_label calls={len(sends)} "
      f"drop-offs={len(world.dropoffs)} live labels={len(world.live_labels('2001'))}")
print("ch03 solution: OK")
