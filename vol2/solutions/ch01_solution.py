"""Chapter 1 exercise: move a ticket down a rung.

Move "address change" from the agent rung to the router rung (a fixed track the code
lays: look up, change if still packing, else escalate) and rerun parcel #6001.
"""
from _path import STUB

import ch01
from world import World

agent_world, low_world = World(), World()
agent = ch01.harness(agent_world).run(ch01.ADDRESS, "address change", ch01.ASHA,
                                      "T-6001-a", echo=False)

h = ch01.harness(low_world)
h.rungs["address change"] = "router"          # the change: one rung down
low = h.run(ch01.ADDRESS, "address change", ch01.ASHA, "T-6001-r")

# Checked on world state, not on printed lines.
assert low_world.carrier_asks == 0, "the router rung never offers ask_carrier"
assert low_world.addresses == {}, "an in-transit parcel keeps its address"
assert low["outcome"].startswith("escalate"), low["outcome"]
assert len(low["steps"]) == 1
if STUB:
    assert agent_world.carrier_asks == 1 and len(agent["steps"]) == 2
    assert len(low["steps"]) < len(agent["steps"])
print(f"steps: agent rung={len(agent['steps'])} router rung={len(low['steps'])}; "
      f"ask_carrier calls: agent rung={agent_world.carrier_asks} router rung=0")
print("ch01 solution: OK")
