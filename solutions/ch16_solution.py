"""Chapter 16 exercise: try to fool the gate.

1. Ask "Do you price match if I find it cheaper?" with the cite-only rules. Print the
   reply, its receipts and the gate's verdict.
2. Hand the gate a reply that cites [S9], a passage that was never retrieved.
3. Ask the battery question. Does a supported answer pass?
Run: python3 solutions/ch16_solution.py
"""
import _path  # noqa: F401
from ch15 import augment, generate, index, retrieve
from ch16 import ABSTAIN, CITE_ONLY, grounded, passage_gate, receipts

if __name__ == "__main__":
    q = "Do you price match if I find it cheaper?"
    passages = retrieve(q, index())
    loose = generate(augment(passages, CITE_ONLY), q)
    verdict = passage_gate(loose, passages)
    print("reply:", loose, "| receipts:", receipts(loose), "| gate:", verdict)
    fake = passage_gate("answer: Refunds take 2 days [S9].", passages)
    print("fake receipt:", fake)
    battery = grounded("My NW-500 battery stopped charging. Is it covered?")
    print("battery:", battery)
    assert receipts(loose) == ["R4"] and verdict == (False, "the cited passage does not say this")
    assert fake == (False, "cites a passage we did not retrieve")
    assert grounded(q, rules=CITE_ONLY)[0] == ABSTAIN
    assert battery[1] == "ok" and "[S2]" in battery[0]
    print("ch16 solution: OK")
