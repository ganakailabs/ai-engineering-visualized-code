"""Chapter 13: Security Engineering, Threat Modeling and Red-Teaming.

Run from the repo root:  python3 vol4/ch13.py
SCRIPTED attacks on a deliberately gullible stub model (see security.py); no real
model is attacked here. Part 1: the threat table, then the BREAK (the model was the
only check) and the FIX (the tool checks the session). Part 2: the fix that shipped
for the known attacks, then the held-out and multi-turn variants, then coverage.
Part 3: one turn of the red-team loop on a poisoned memory note.
"""
import _root  # noqa: F401

import security as S

ASHA = {"customer": "asha", "tenant": "a", "task": "refund_request"}


def held_out_report(flt):
    held = [S.run_attack(x, flt, ASHA) for x in S.HELD_OUT]
    multi = [S.run_attack(x, flt, ASHA) for x in S.MULTI_TURN]
    for x, r in zip(S.HELD_OUT + S.MULTI_TURN, held + multi):
        state = "blocked" if r["blocked"] else "missed "
        print(f"  {x['id']} {x['channel']:<9} {state} tool={r['tool']}"
              f"{' ' + r['why'] if r['why'] else ''}")
    hb = sum(r["blocked"] for r in held)
    mb = sum(r["blocked"] for r in multi)
    print(f"held_out variants blocked={hb}/{len(held)} "
          f"multi_turn blocked={mb}/{len(multi)}")
    return held + multi


if __name__ == "__main__":
    print("== Part 1: doors, boundaries, and the only check ==")
    print(f"{'channel':<13}{'boundary':<18}check")
    for c in S.CHANNELS:
        b, _, chk = S.THREATS[c]
        print(f"{c:<13}{b:<18}{chk}")
    print("worst action at every door: refund another order")
    print(f"{'asset':<14}{'operation':<18}{'task allows':<18}enforced at")
    for asset, op, task, where in S.ASSETS:
        print(f"{asset:<14}{op:<18}{task:<18}{where}")
    none = S.Filter()
    r = S.run_attack(S.KNOWN[0], none, ASHA, trusting=True)
    print(f"BREAK tool trusts model: refund {r['tool']} order={r['target']}"
          f" owner={S.ORDERS[r['target']]['owner']}")
    r = S.run_attack(S.KNOWN[0], none, ASHA)
    print(f"boundary tools: model fooled={'yes' if r['obeyed'] else 'no'} "
          f"refund {r['tool']} {r['why']}")
    print(f"own order: refund {S.issue_refund(ASHA, '2001')[0]}; "
          f"large order: {' '.join(S.issue_refund(ASHA, '2002'))}")

    print("== Part 2: known attacks, new variants ==")
    flt = S.Filter([r"ignore (all )?previous instructions"])
    print("fix shipped: filter pattern 'ignore (all) previous instructions'")
    for x in S.KNOWN:
        r = S.run_attack(x, flt, ASHA)
        print(f"  channel={x['channel']:<9} known="
              f"{'blocked' if r['blocked'] else 'missed'}")
    print("held-out set opened once, after the fix:")
    results = held_out_report(flt)
    assert all(r["tool"] != "issued" for r in results)
    followed, harmful = S.report(results)
    print(f"model followed the injection {followed}/{len(results)}; "
          f"harmful outcome {harmful}/{len(results)}")
    print(f"cross-customer refund boundary held on the {len(results)} "
          f"tested variants: yes")
    cov = S.coverage(S.KNOWN + S.HELD_OUT + S.MULTI_TURN)
    for c in S.CHANNELS:
        print(f"coverage channel={c:<13}tested="
              f"{'yes' if cov[c] else 'no'} cases={cov[c]}")

    print("== Part 3: red-team loop, memory ==")
    r = S.run_attack(S.POISONED_MEMORY, S.Filter(), ASHA)
    print(f"attack R1 memory note (no filter on memory reads): "
          f"obeyed={'yes' if r['obeyed'] else 'no'}")
    print(f"log hit R1 -> tool {r['tool']} {r['why']}")
    S.KNOWN.append(S.POISONED_MEMORY)
    print(f"add to evals: known suite now {len(S.KNOWN)} cases")
    r = S.run_attack(S.POISONED_MEMORY, flt, ASHA)
    print(f"fix: memory reads pass the filter -> R1 "
          f"{'blocked' if r['blocked'] else 'missed'}")
    cov = S.coverage(S.KNOWN)
    print(f"coverage channel=memory tested={'yes' if cov['memory'] else 'no'}"
          f" cases={cov['memory']}")

    print("== Part 4: same customer, wrong task; disclosure ==")
    ship = dict(ASHA, task="delivery_status")
    r = S.run_attack(S.WRONG_TASK, S.Filter(), ship)
    print(f"W1 courier note on a delivery question asks: refund own #{r['target']}")
    print(f"  model followed={'yes' if r['obeyed'] else 'no'} -> refund {r['tool']}"
          f" ({r['why']})")
    print(f"  same order, refund_request task -> refund "
          f"{S.issue_refund(ASHA, '2001')[0]}")
    d = S.run_disclosure(S.DISCLOSURE, ship)
    print(f"D1 review asks for #3001's address: model followed="
          f"{'yes' if d['obeyed'] else 'no'}")
    print(f"  -> read {d['tool']} ({d['why']}), nothing disclosed")
    print(f"  own order, delivery task -> read "
          f"{S.order_details(ship, '2001')[0]}")
