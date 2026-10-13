"""Chapter 18: Workflows vs Agents: Rails or Steering Wheel."""
from stub_model import call_model
from ch11 import handle as decide_refund         # Ch 11: tool call + checked JSON decision
from ch16 import grounded                         # Ch 16: answer from passages, or abstain


# MM-049: rails. Your code lays the track; the model fills in one step.
def refund_track(ticket):
    reply, _ = decide_refund(ticket)               # fixed: look up, decide, check, repair once
    return f"{reply['decision']} ({reply['clause']})"


def answer_track(ticket):
    return grounded(ticket)[0]                     # fixed: retrieve, answer, gate


def person_track(ticket):
    return "escalate: passed to a person"


# MM-050, rung 2: a router. The model picks the track; every track is still fixed.
ROUTER = "Classify the ticket: refund, tracking, warranty or other. Reply with one word."
TRACKS = {"refund": refund_track, "tracking": answer_track,
          "warranty": answer_track, "other": person_track}


def route(ticket, model=call_model):
    label = model([{"role": "system", "content": ROUTER},
                        {"role": "user", "content": ticket}])["text"].strip()
    if label not in TRACKS:                        # check the label like any model output
        label = "other"
    return label, TRACKS[label](ticket)


# MM-050: the autonomy ladder. 1 fixed chain, 2 router, 3 agent. Least that works.
RUNG = {"refund": 1, "tracking": 1, "warranty": 1,   # each track alone is a fixed chain
        "whole inbox": 2,                            # the router picks the track
        "change address": 3}                         # steps depend on what it finds: Ch 19

if __name__ == "__main__":
    for ticket in ("Refund for #4410, please", "Where is my parcel?",
                   "My NW-500 battery stopped charging", "Can you change my delivery address?"):
        label, out = route(ticket)
        print(f"{ticket!r:40} -> {label:8} -> {out[:70]}")
    print("rungs:", RUNG)
