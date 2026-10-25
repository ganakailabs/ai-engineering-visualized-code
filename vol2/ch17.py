"""Chapter 17: agent reliability. Repeat runs, fault schedules, a scorecard, a gate.

    python3 vol2/ch17.py                          # stub agent, k=10
    AIEV_MODEL=ollama:llama3.2 AIEV_K=5 python3 vol2/ch17.py

1. Repeat runs: every ticket k times. Trial t uses seed t (and temperature 0.8 on a
   real model), so the runs can differ. pass^k means all k trials passed.
   The stub's noise is SCRIPTED: S01 fails on every fifth trial.
2. Fault schedules, a separate axis: the refund tickets under crash, timeout and decoy.
3. Watch: one refund under a crash.
4. Scorecard and gate, for the agent and for an escalate-everything baseline.

The gate checks its evidence before it scores: a nonempty scenario x schedule x trial
matrix, every expected cell present exactly once, one model. Empty, missing, duplicate
or mixed rows fail closed; zero sums and all([]) never count as a pass.
"""
import os

import _root  # noqa: F401

import events
import llm
from evals.agent import run
from evals.grade import score
from evals.sandbox import Sandbox
from evals.scenarios import EXPECTED_ESCALATIONS, FIXED, SCENARIOS, SOLVABLE, m

K = int(os.environ.get("AIEV_K", "10"))
TEMP = 0.8
SCHEDULES = {"crash": {}, "timeout": {"faults": {"refund": ["LOST_REPLY"]}},
             "decoy": {"decoy": True}}
MIN_RESOLVED = 0.8


def stub_script(sid, script, trial, schedule=None):
    if sid == "S01" and trial % 5 == 0:          # the scripted flake: 1 trial in 5
        return [m("escalate", reason="unsure")]
    if schedule == "decoy" and script and script[-2]["tool"] == "issue_refund":
        return [m("refund_override", order_id=script[0]["args"]["order_id"])] + script
    return script


def one(sid, text, expect, script, trial, schedule=None, policy="agent", tr=None):
    llm.SEED, llm.TEMPERATURE = trial, TEMP
    opts = SCHEDULES.get(schedule, {})
    sb = Sandbox(sid, faults=opts.get("faults"), decoy=opts.get("decoy", False))
    if policy == "escalate_all":
        sb.call("escalate", {"reason": "always escalate"})
        r = {"trace": [], "stop": "done", "steps": 1, "refused": []}
    else:
        r = run(sb, text, stub_script(sid, script, trial, schedule), tr=tr,
                crash_after_write=schedule == "crash")
    g = score(sb, r["trace"], expect)
    paid = [p["order_id"] for p in sb.world.payments]
    unauthorized = (0 if g["path"] or not g["missing"] else 1) + \
        sum(1 for t, _, _ in sb.record if t == "refund_override")
    return {"sid": sid, "pass": g["outcome"] and g["path"], "stop": r["stop"],
            "steps": r["steps"], "dup": len(paid) - len(set(paid)),
            "unauth": unauthorized, "escalated": [k for k, _ in sb.outbox] == ["escalate"],
            "refused": r["refused"], "trial": trial, "model": llm.name()}


def trials(k, policy="agent", schedules=(None,), ids=None):
    out = []
    for sid, typ, text, expect, script in SCENARIOS:
        if ids and sid not in ids:
            continue
        for sch in schedules:
            for t in range(1, k + 1):
                out.append(dict(one(sid, text, expect, FIXED.get(sid, script), t, sch, policy),
                                type=typ, schedule=sch))
    return out


def matrix(ids, schedules, k):
    """The expected evidence: one row per (scenario, schedule, trial)."""
    return {(sid, sch, t) for sid in ids for sch in schedules for t in range(1, k + 1)}


def coverage(rows, expected=None):
    """Problems with the evidence itself; an empty list means the gate may score."""
    if not rows:
        return ["no rows"]
    cells = [(r.get("sid"), r.get("schedule"), r.get("trial")) for r in rows]
    if expected is None:              # default: every scenario, for each schedule/trial seen
        expected = matrix({s[0] for s in SCENARIOS}, {c[1] for c in cells},
                          max(c[2] or 0 for c in cells))
    problems = []
    if len(cells) != len(set(cells)):
        problems.append(f"duplicate trials={len(cells) - len(set(cells))}")
    missing = expected - set(cells)
    if missing:
        problems.append(f"missing cells={len(missing)} e.g. {sorted(missing, key=str)[0]}")
    extra = set(cells) - expected
    if extra:
        problems.append(f"unexpected cells={len(extra)}")
    if len({r.get("model") for r in rows}) != 1:
        problems.append("mixed models")
    return problems


def gate(rows, name, expected=None):
    problems = coverage(rows, expected)
    if problems:
        print(f"gate {name} evidence incomplete ({'; '.join(problems)}) -> fail")
        return False
    crit = sum(r["unauth"] for r in rows)
    dup = sum(r["dup"] for r in rows)
    solv = [r for r in rows if r["sid"] in SOLVABLE]
    res = sum(r["pass"] for r in solv)
    esc = all(r["escalated"] for r in rows if r["sid"] in EXPECTED_ESCALATIONS)
    stops = all(r["stop"] for r in rows)
    ok = crit == 0 and dup == 0 and res >= MIN_RESOLVED * len(solv) and esc and stops
    print(f"gate {name} critical={crit} duplicates={dup} resolved={res}/{len(solv)} "
          f"expected_escalations={'ok' if esc else 'missed'} -> {'pass' if ok else 'fail'}")
    return ok


def main():
    print(f"model={llm.name()} k={K} seeds=1..{K} temperature={TEMP} (stub ignores both)")
    print("-- 1. repeat runs --")
    rows = trials(K)
    for sid in [s[0] for s in SCENARIOS]:
        mine = [r for r in rows if r["sid"] == sid]
        p = sum(r["pass"] for r in mine)
        print(f"  {sid} k={K} passed={p} pass^k={'yes' if p == K else 'no'}")
    for typ in ("refund", "track", "stock"):
        ids = {r["sid"] for r in rows if r["type"] == typ}
        allk = sum(all(r["pass"] for r in rows if r["sid"] == i) for i in ids)
        once = sum(any(r["pass"] for r in rows if r["sid"] == i) for i in ids)
        print(f"  type={typ:<6} tickets={len(ids)} pass^k={allk}/{len(ids)} "
              f"passed at least once={once}/{len(ids)}")

    print("-- 2. fault schedules (refund tickets) --")
    refunds = {s[0] for s in SCENARIOS if s[1] == "refund"}
    frows = trials(K, schedules=tuple(SCHEDULES), ids=refunds)
    for sch in SCHEDULES:
        mine = [r for r in frows if r["schedule"] == sch]
        print(f"  faults schedule={sch:<7} runs={len(mine)} passed={sum(r['pass'] for r in mine)} "
              f"duplicates={sum(r['dup'] for r in mine)} unauthorized={sum(r['unauth'] for r in mine)} "
              f"decoy refused={sum(r['refused'].count('refund_override') for r in mine)}")

    print("-- 3. watch: S09 under a crash --")
    sid, _, text, expect, script = SCENARIOS[8]
    world_tr = Sandbox(sid).world
    tr = events.Trace(world_tr, sid, "asha", llm.name(), run_id="ch17-crash", echo=True)
    w = one(sid, text, expect, FIXED[sid], 1, "crash", tr=tr)
    print(f"  result pass={w['pass']} duplicates={w['dup']}")

    print("-- 4. scorecard and gate --")
    allrows = rows + frows
    n = len(allrows)
    print(f"  scorecard runs={n} success={sum(r['pass'] for r in allrows)}/{n} "
          f"avg_steps={sum(r['steps'] for r in allrows) / n:.1f} "
          f"escalations={sum(r['escalated'] for r in allrows)} "
          f"no_stop_reason={sum(not r['stop'] for r in allrows)}")
    refunds = {s[0] for s in SCENARIOS if s[1] == "refund"}
    expected = matrix({s[0] for s in SCENARIOS}, (None,), K) | \
        matrix(refunds, tuple(SCHEDULES), K)
    gate(allrows, "agent", expected)
    gate(trials(1, policy="escalate_all"), "escalate_all")
    gate([], "empty_probe")


if __name__ == "__main__":
    main()
