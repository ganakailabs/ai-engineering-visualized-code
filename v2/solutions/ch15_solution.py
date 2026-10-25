"""Chapter 15 exercise: let the courier recover.

After the retry storm the courier breaker is OPEN. The courier recovers; advance the
world clock two simulated minutes. A cancel from the customer arrives while the trial
call is in flight.
Predict first: how many trial calls, and does the cancel win?
Expected: HALF_OPEN, one trial call, `breaker CLOSED`; the trial replays the label
already sent (same key, no new label); the cancel is applied at the next safe state,
after the trial returns and before any further step. Asserted on the world.
"""
import _path  # noqa: F401

from cascade import run_fix, schedule


def main():
    r = run_fix(schedule(), log=lambda *_: None)
    world, br = r["world"], r["breakers"]["courier"]
    assert br.state == "OPEN"
    calls_before = world.courier_calls
    world.courier.clear()                          # the courier recovers
    br.log = print
    world.tick(2)                                  # hint: the world clock, not real time
    cancel = []
    steps = []

    def trial():
        cancel.append("cancel from customer")      # arrives while the call is in flight
        return world.send_label("2001", "Ceramic mug set", key="k-T-2001-label")

    receipt = br.call(trial)
    print(f"trial receipt={receipt['receipt_id']} replayed={receipt.get('replayed', False)}")
    print(f"breaker {br.name} {br.state} trials={br.trials}")
    if cancel:                                     # the next safe state: between steps
        steps.append("stop cancelled")
    else:
        steps.append("reply label sent")
    print(f"next step: {steps[-1]}")
    assert br.trials == 1 and br.state == "CLOSED"
    assert world.courier_calls == calls_before + 1
    assert receipt.get("replayed") is True
    assert len(world.live_labels("2001")) == 1 and len(world.payments_for("2001")) == 1
    assert steps == ["stop cancelled"]
    print("ch15 solution: OK")


if __name__ == "__main__":
    main()
