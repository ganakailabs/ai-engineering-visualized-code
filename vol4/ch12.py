"""Chapter 12: When to Fine-Tune, Distill or Change Models.

Run from the repo root:  python3 vol4/ch12.py
Tickets and teacher labels are SIMULATED (seeded templates; see triage.py). Part 1 is
the BREAK: split before dedup, train on raw teacher labels, grade against the teacher.
Part 2 is the FIX: dedup, split by ticket, open the TRY gate, review a label sample,
send the confused slice to humans, train the student, then open the held-out test set
once and decide at the SHIP gate.
Part 3 holds out whole template families (related tickets exact dedup cannot catch),
and shows a noninferiority ship policy beside this lab's superiority policy.
"""
import _root  # noqa: F401

import random
import re

import triage as T

# Example scores from the last four prompt iterations on triage (simulated).
PROMPT_HISTORY = [0.931, 0.938, 0.940, 0.940]
DAMAGED = re.compile(r"arrived (cracked|broken)")


def plateau(history, min_gain=0.005):
    return history[-1] - history[-2] < min_gain


def train(rows, labels):
    return T.NaiveBayes().fit([t["text"] for t in rows], labels)


def report(name, pred, gold):
    print(f"  {name:<8} acc={T.accuracy(pred, gold):.3f} "
          f"critical={T.critical(pred, gold)}")


if __name__ == "__main__":
    raw = T.make_tickets()
    teacher = {t["id"]: T.teacher_label(t) for t in raw}

    print("== Part 1: BREAK, split first, grade against the teacher ==")
    tr, _, te = T.split(raw)
    seen = {t["text"] for t in tr}
    leaked = sum(t["text"] in seen for t in te)
    m = train(tr, [teacher[t["id"]] for t in tr])
    pred = [m.predict(t["text"]) for t in te]
    print(f"split before dedup: test={len(te)} also in train={leaked}")
    print(f"student vs TEACHER labels: acc="
          f"{T.accuracy(pred, [teacher[t['id']] for t in te]):.3f}"
          "  (looks fine)")
    dmg = [i for i, t in enumerate(te) if DAMAGED.search(t["text"])]
    ok = sum(pred[i] == te[i]["human"] for i in dmg)
    print(f"damaged-on-arrival vs HUMAN labels: {ok}/{len(dmg)} right")

    print("\n== Part 2: FIX, clean data, two gates ==")
    clean = T.dedup(raw)
    tr, va, te = T.split(clean)
    print(f"data tickets={len(raw)} dedup removed={len(raw) - len(clean)}")
    print(f"split train/val/test by ticket = "
          f"{len(tr)}/{len(va)}/{len(te)}")
    opened, why = T.gate_try(plateau(PROMPT_HISTORY), len(tr))
    print(f"gate try plateau={'yes' if plateau(PROMPT_HISTORY) else 'no'} "
          f"labelled={len(tr)} -> {'open' if opened else 'closed'} "
          f"{' '.join(why)}".rstrip())

    sample = random.Random(5).sample(tr, 60)
    found = T.review(sample, teacher)
    slice_hits = sum(bool(DAMAGED.search(t["text"])) for t, _, _ in found)
    print(f"review sample=60 disagree={len(found)} "
          f"damaged-on-arrival={slice_hits}")
    labels, relabelled = [], 0
    for t in tr:
        if DAMAGED.search(t["text"]):
            labels.append(t["human"])              # slice sent to humans
            relabelled += 1
        else:
            labels.append(teacher[t["id"]])
    print(f"slice sent for human labels: {relabelled} train tickets")
    m = train(tr, labels)
    v = [m.predict(t["text"]) for t in va]
    print(f"validation (while building): student acc="
          f"{T.accuracy(v, [t['human'] for t in va]):.3f}")

    gold = [t["human"] for t in te]
    stu = [m.predict(t["text"]) for t in te]
    cur = [teacher[t["id"]] for t in te]
    print(f"held-out test, HUMAN labels, n={len(te)} (simulated):")
    report("teacher", cur, gold)
    report("student", stu, gold)
    gain = T.accuracy(stu, gold) - T.accuracy(cur, gold)
    crit = T.critical(stu, gold)
    shipped, why = T.gate_ship(gain, crit)
    print(f"gate ship gain={gain:+.3f} critical={crit} -> "
          f"{'open' if shipped else 'closed'} {' '.join(why)}".rstrip())
    pc = T.per_class(stu, gold)
    print("  student per class: " + " ".join(
        f"{k}={r}/{n}" for k, (r, n) in sorted(pc.items())))
    money = pc["refund"][1] + pc["warranty"][1]
    print(f"  critical=0 in {money} money questions: 95% bound about "
          f"{T.zero_fail_bound(money):.1%}, not zero")

    print("\n== Part 3: related tickets, and the policy ==")
    held = {f"{x}/0" for x in T.TYPES}          # one template family per type
    gtr, gte = T.split_groups(clean, lambda t: t["family"], held)
    glab = [t["human"] if DAMAGED.search(t["text"]) else teacher[t["id"]] for t in gtr]
    gm = train(gtr, glab)
    ggold = [t["human"] for t in gte]
    gstu = [gm.predict(t["text"]) for t in gte]
    gcur = [teacher[t["id"]] for t in gte]
    print(f"held out by template family (one per type), n={len(gte)}:")
    report("teacher", gcur, ggold)
    report("student", gstu, ggold)
    ggain = T.accuracy(gstu, ggold) - T.accuracy(gcur, ggold)
    ok, why = T.gate_ship(ggain, T.critical(gstu, ggold))
    print(f"gate ship gain={ggain:+.3f} -> {'open' if ok else 'closed'} "
          f"{' '.join(why)}".rstrip())
    ok, why = T.gate_ship(-0.010, 0, policy="noninferior", margin=0.02, cheaper=True)
    print(f"policy noninferior margin=0.02, cheaper, example gain=-0.010 -> "
          f"{'open' if ok else 'closed'}")
