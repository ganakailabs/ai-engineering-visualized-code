"""Chapter 7 exercise: race the courier.

The courier's reply and the 3-day timeout land in the same simulated tick. Whichever
commits first wins; the other is logged stale. Run it in both orders.
"""
from _path import STUB  # noqa: F401

import ch07

for first in ("courier_reply", "timeout"):
    print(f"--- {first} first ---")
    world, store, w, armed = ch07.setup()
    world.tick(3 * 24 * 60)                          # the timer is due this very tick
    if first == "courier_reply":
        w.deliver(ch07.T, "courier_reply", armed)
        w.fire_due()
    else:
        w.fire_due()
        w.deliver(ch07.T, "courier_reply", armed)
    moves = [s for _, s, _ in store.history(ch07.T)][5:]          # after WAITING_COURIER
    stale = [e for e in w.tr.of("observe") if "stale" in e["text"]]
    # exactly one winning commit; the courier path then records intent before the
    # label effect (LABEL_PENDING) and confirms it after (LABEL_SENT)
    want = ["LABEL_PENDING", "LABEL_SENT"] if first == "courier_reply" else ["HANDOFF"]
    assert moves == want, moves
    assert len(stale) == 1
    assert len(world.live_labels("2001")) == 1 and len(world.labels) == 1

# what the customer writes is read by the model; the cancel rules decide
for message in ("Where is my swap? It has been two days.",
                "Please cancel the swap, I will keep the cracked set."):
    world, store, intent = ch07.customer_writes(message)
    current = store.load(ch07.T)[0]
    assert world.payments == [] and len(world.labels) == 1
    assert current == ("CANCELLED" if intent == "cancel" else "LABEL_SENT"), current
    if intent == "cancel":
        assert world.live_labels("2001") == [], "the label is voided before the cancel"
    if STUB:
        assert intent == ("cancel" if "cancel" in message else "status")
print("ch07 solution: OK")
