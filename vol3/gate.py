"""Synthetic test sets and the regression gate (Vol 3 Ch 16).

A scripted generator (a stand-in for a model) proposes questions from the
handbook; code review rejects ungrounded, leaking and duplicate ones; a hash
splits the rest into dev and held-out. gate_results() compares a change with
the baseline case by case: critical failures block, any case the baseline got
right and the change gets wrong blocks (MAX_NEW_FAILURES, a declared
non-regression policy), missing case results block, a paired difference inside
its bootstrap interval is not a win, and a system that answers too few
answerable cases fails even with zero wrong answers.

This gate demonstrates critical-case vetoes, a non-regression policy and minimum
quality checks on SCRIPTED results. A release decision needs real case outputs,
graded, and a regression policy the team has agreed on. The hash split keeps the
same question text on the same side; it does not stop semantic leakage (a
paraphrase of a held-out question can still land in dev).
"""
import hashlib
import random

import _root  # noqa: F401
from store import HANDBOOK

# ---------- the synthetic question factory ----------

PROPOSED = [  # (passage, question, expected answer span)
    ("S5", "How long do EU customers have to withdraw from an online purchase?", "14 days"),
    ("S5", "How many days do EU customers get to withdraw from an online order?", "14 days"),
    ("S5", "Do EU customers need to give a reason to withdraw?", "without giving a reason"),
    ("S2", "How long is the NW-500 warranty?", "12-month"),
    ("S2", "Is a battery that stops charging a defect?", "counts as a defect"),
    ("S2", "Does the 12-month warranty cover accidental drops?", "accidental damage"),
    ("S3", "Who pays return shipping for a damaged item?", "free for damaged items"),
    ("S3", "Who pays return shipping for other returns?", "the customer pays"),
    ("S4", "Can gift cards be exchanged for cash?", "cannot be exchanged for cash"),
    ("S1", "How long do orders usually take to arrive?", "5 business days"),
    ("S1", "How do I track my parcel?", "link in the shipping email"),
    ("S1", "Do orders arrive within 5 business days?", "5 business days"),
]


def _words(t):
    return set(t.lower().replace("?", "").split())


def review(proposed=PROPOSED):
    """Returns (approved, rejected with reasons). Code checks; a person signs off."""
    ok, bad = [], []
    for pid, q, a in proposed:
        if a.lower() not in HANDBOOK[pid].lower():
            bad.append((q, "answer not in passage"))
        elif a.lower() in q.lower():
            bad.append((q, "question gives away the answer"))
        elif any(len(_words(q) & _words(p)) / len(_words(q) | _words(p)) >= 0.5
                 for _, p, _ in ok):
            bad.append((q, "near-duplicate"))
        else:
            ok.append((pid, q, a))
    return ok, bad


def split(approved):
    """Stable split: the same question always lands on the same side."""
    dev, held = [], []
    for case in approved:
        n = int(hashlib.sha1(case[1].encode()).hexdigest(), 16)
        (held if n % 4 == 3 else dev).append(case)
    return dev, held

# ---------- the held-out benchmark and the gate ----------

# (case id, category, answerable, critical)
BENCH = [
    ("eu-withdrawal", "tables", True, True),
    ("in-battery-row", "tables", True, False),
    ("refund-vs-ticket", "conflicts", True, True),
    ("old-vs-new-window", "conflicts", True, True),
    ("supplier-vs-policy", "conflicts", True, False),
    ("other-tenant-note", "permissions", True, True),
    ("internal-only-page", "permissions", True, True),
    ("revoked-page", "permissions", True, False),
    ("retired-clause", "outdated", True, True),
    ("stale-order-total", "outdated", True, False),
    ("bundle-charger", "multi-hop", True, False),
    ("bundle-stand", "multi-hop", True, False),
    ("final-sale-refund", "decisions", True, False),
    ("gift-card-cash", "abstain", False, False),
    ("lifetime-warranty", "abstain", False, False),
    ("unknown-part", "abstain", False, True),
]
CAT = {c: cat for c, cat, _, _ in BENCH}
MIN_ANSWER_RATE = 0.8
MAX_NEW_FAILURES = 0      # declared policy: no case the baseline passed may now fail

# For each scripted system: the ids it gets wrong ("abstain_all" abstains everywhere).
SYSTEMS = {
    "baseline": {"bundle-stand", "in-battery-row", "stale-order-total"},
    "chunking_change": {"eu-withdrawal"},                 # mean up, critical broken
    "chunking_fixed": {"stale-order-total"},
    "no_precedence": {"refund-vs-ticket", "old-vs-new-window", "supplier-vs-policy",
                      "bundle-stand"},
}


def results(system):
    """Per case: (correct, abstained)."""
    out = {}
    for c, _, answerable, _ in BENCH:
        if system == "abstain_all":
            out[c] = (not answerable, True)
        else:
            wrong = c in SYSTEMS[system]
            out[c] = (not wrong, (not answerable) and not wrong)
    return out


def paired_interval(base, new, n_boot=2000, seed=7, bench=None):
    """Mean of per-case differences and a 95% percentile bootstrap interval."""
    d = [int(new[c][0]) - int(base[c][0]) for c, *_ in (bench or BENCH)]
    rng = random.Random(seed)
    means = sorted(sum(rng.choice(d) for _ in d) / len(d) for _ in range(n_boot))
    return sum(d) / len(d), (means[int(0.025 * n_boot)], means[int(0.975 * n_boot) - 1])


def gate_results(base, new, bench=None, max_new_failures=MAX_NEW_FAILURES):
    """Gate per-case records {case id: (correct, abstained)} for a baseline and a
    change. A case missing from either side blocks; it is never counted as a pass.
    Returns verdict ("pass" | "blocked") and a label that never calls a pass with an
    interval touching zero an improvement."""
    bench = bench or BENCH
    ids = [c for c, *_ in bench]
    missing = sorted(c for c in ids if c not in new or c not in base)
    if missing:
        return dict(verdict="blocked", label="blocked",
                    reasons=[f"missing results for {len(missing)} cases: {', '.join(missing)}"],
                    missing=missing, critical=[], new_failures=[])
    crit = [c for c, _, _, critical in bench if critical and not new[c][0]]
    new_fail = [c for c in ids if base[c][0] and not new[c][0]]
    ans = [c for c, _, a, _ in bench if a]
    answered = sum(new[c][0] for c in ans)
    abst = [c for c, _, a, _ in bench if not a]
    abstained = sum(new[c][1] for c in abst)
    diff, (lo, hi) = paired_interval(base, new, bench=bench)
    reasons = []
    if crit:
        reasons.append(f"critical failures={len(crit)}")
    if len(new_fail) > max_new_failures:
        reasons.append(f"new failures={len(new_fail)} > {max_new_failures} allowed")
    if answered / len(ans) < MIN_ANSWER_RATE:
        reasons.append(f"answered {answered}/{len(ans)} < {MIN_ANSWER_RATE:.0%}")
    if abstained < len(abst):
        reasons.append(f"abstained {abstained}/{len(abst)} expected")
    verdict = "blocked" if reasons else "pass"
    label = ("blocked" if reasons else
             f"pass within tolerance ({len(new_fail)} new failures allowed by policy)" if new_fail else
             "pass, improvement demonstrated" if lo > 0 else
             "pass, no regression found (improvement not demonstrated)")
    return dict(verdict=verdict, label=label, reasons=reasons, missing=[], critical=crit,
                new_failures=new_fail, answered=answered, answerable=len(ans),
                abstained=abstained, expected_abstain=len(abst), diff=diff,
                interval=(lo, hi), win=lo > 0,
                mean=sum(new[c][0] for c in ids) / len(ids))


def gate(base_name, new_name):
    """The scripted systems above, through gate_results()."""
    return gate_results(results(base_name), results(new_name))
