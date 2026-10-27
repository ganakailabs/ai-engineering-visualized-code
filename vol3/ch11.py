"""Chapter 11: Context Assembly: Packing Evidence for the Model.

Run from the repo root:  python3 vol3/ch11.py
Eight precedence-checked passages become a deduplicated, labelled pack inside a token
budget; the reply's citations are validated against the pack; coverage per k is
measured on held-out labelled questions. The answering model is a stub unless
AIEV_MODEL is set.
"""
import _root  # noqa: F401

import assemble as A

Q = "can I return my clearance jacket, and do I need a photo?"

if __name__ == "__main__":
    print("Part 1 (MM-150): assemble the pack")
    pack, s = A.assemble(A.EIGHT)
    print(f"  assemble in={s['n_in']} dupes={s['dupes']} kept={s['kept']} "
          f"tokens={s['tokens']} budget={s['budget']} over_budget={s['over']}")
    print("  " + A.render(pack).replace("\n", "\n  "))

    action, reply = A.answer(Q, pack)
    ok, cited, unknown = A.validate_citations(reply, pack)
    print(f"  reply  {reply}")
    print(f"  check  citations=[{','.join(cited)}] in pack={'yes' if ok else 'no'} -> {action}")

    phantom = "Returns are 30 days [S1], and photos are optional [S7]."
    ok, cited, unknown = A.validate_citations(phantom, pack)
    print(f"  break  citations=[{','.join(cited)}] unknown={unknown} -> "
          f"{'send' if ok else 'escalate'}")

    print("\nPart 2 (MM-151): coverage per k on held-out questions")
    for k in (2, 3, 5, 10):
        hit, n = A.coverage(k)
        print(f"  k={k:<2} coverage={hit}/{n}")
