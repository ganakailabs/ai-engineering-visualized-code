"""Chapter 11 exercise: sweep k from 2 to 10.

Predict first: does coverage keep rising? Coverage is printed per k; every cited id is
checked against the pack at every k. Answer accuracy per k needs a real model:
[TO MEASURE] (see vol3/runs/README.md).
"""
import _path  # noqa: F401

import assemble as A

prev = 0
for k in range(2, 11):
    hit, n = A.coverage(k)
    assert hit >= prev
    prev = hit
    for q, _ in A.HELD_OUT:
        pack = A.pack_for(q, k)
        action, reply = A.answer(q, pack)
        ok, cited, unknown = A.validate_citations(reply, pack)
        assert action == ("send" if ok else "escalate")
        assert not (action == "send" and unknown)
    print(f"k={k:<2} coverage={hit}/{n}")
print("ch11 solution: OK")
