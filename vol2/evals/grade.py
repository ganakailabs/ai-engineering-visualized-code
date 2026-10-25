"""Chapter 16 (MM-115): grade the outcome and the path separately.

outcome: from the world and the outbox (what changed), never from the agent's words.
path:    ordering constraints over the sandbox's own tool-call record. Only the listed
         pairs are required; any other order of reads is a valid path.
labels:  steps the agent CLAIMS in its trace but the record never saw score nothing.
"""
REFUND_RULES = [("look_up_order", "issue_refund"),
                ("check_eligibility", "issue_refund")]
CHANGES_ORDER = {"update_order"}       # a check made before one of these is stale
NEGATIONS = {"not", "no", "never", "don't", "isn't", "won't", "cannot"}


def says_it(reply, phrase):
    """The phrase appears and is not negated by the two words before it."""
    words, want = reply.lower().split(), phrase.lower().split()
    for i in range(len(words) - len(want) + 1):
        if [w.strip(".,;:!?'\"") for w in words[i:i + len(want)]] == want:
            if not NEGATIONS & set(words[max(0, i - 2):i]):
                return True
    return False


def grade_outcome(sandbox, expect):
    """expect: {"payments": [(order_id, amount)], "kind": reply|escalate|ask,
    "says": substring the reply must contain or None}."""
    got = sorted((p["order_id"], p["amount"]) for p in sandbox.world.payments)
    if got != sorted(expect["payments"]):
        return False, f"payments={got} expected={sorted(expect['payments'])}"
    kinds = [k for k, _ in sandbox.outbox]
    if kinds != [expect["kind"]]:
        return False, f"outbox={kinds} expected=[{expect['kind']}]"
    says = expect.get("says")
    if says and not says_it(sandbox.outbox[0][1], says):
        return False, f"reply lacks {says!r}"
    return True, ""


def grade_path(record, rules=REFUND_RULES):
    """Every `after` call that succeeded needs a successful `before` call on the same
    order earlier in the record, made after the last change to that order.
    Returns (ok, missing)."""
    for i, (tool, args, ok) in enumerate(record):
        oid = args.get("order_id")
        since = max((j + 1 for j, (t, a, _) in enumerate(record[:i])
                     if t in CHANGES_ORDER and a.get("order_id") == oid),
                    default=0)
        for before, after in rules:
            if tool == after and ok and not any(
                    t == before and good and a.get("order_id") == oid
                    for t, a, good in record[since:i]):
                return False, f"{before} before {after}"
    return True, ""


def unbacked_labels(trace, record):
    """Tool names the agent's notes mention that no recorded call backs up."""
    called = {t for t, _, _ in record}
    names = {"look_up_order", "check_eligibility", "issue_refund", "look_up_shipment",
             "stock_of"}
    return sorted(n for n in names if any(n in note for note in trace) and n not in called)


def score(sandbox, trace, expect):
    out_ok, out_why = grade_outcome(sandbox, expect)
    path_ok, missing = grade_path(sandbox.record)
    fakes = unbacked_labels(trace, sandbox.record)
    return {"outcome": out_ok, "outcome_why": out_why, "path": path_ok and not fakes,
            "missing": missing, "fakes": fakes}
