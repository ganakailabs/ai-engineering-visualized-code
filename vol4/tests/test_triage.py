"""Implementation test for Chapter 12: clean splits and the two gates."""
import _path  # noqa: F401

import triage as T


def test_no_ticket_in_two_splits():
    tr, va, te = T.split(T.dedup(T.make_tickets()))
    texts = [{t["text"] for t in s} for s in (tr, va, te)]
    assert not (texts[0] & texts[1] or texts[0] & texts[2] or texts[1] & texts[2])
    print("test_no_ticket_in_two_splits: OK")


def test_split_before_dedup_leaks():
    tr, _, te = T.split(T.make_tickets())
    seen = {t["text"] for t in tr}
    assert any(t["text"] in seen for t in te)
    print("test_split_before_dedup_leaks: OK")


def test_gates_on_named_inputs():
    assert T.gate_try(True, 648) == (True, [])
    assert T.gate_try(True, 100) == (False, ["labelled=100<500"])
    assert T.gate_try(False, 648) == (False, ["plateau=no"])
    assert T.gate_ship(0.06, 0) == (True, [])
    assert T.gate_ship(0.06, 1) == (False, ["critical=1"])
    assert T.gate_ship(0.0, 0) == (False, ["gain=+0.000"])
    # a declared noninferiority policy: within margin AND cheaper may pass...
    assert T.gate_ship(-0.01, 0, "noninferior", 0.02, cheaper=True) == (True, [])
    assert T.gate_ship(-0.03, 0, "noninferior", 0.02, cheaper=True)[0] is False
    assert T.gate_ship(-0.01, 0, "noninferior", 0.02, cheaper=False)[0] is False
    # ...but critical cases bind under every policy
    assert T.gate_ship(-0.01, 1, "noninferior", 0.02, cheaper=True)[0] is False
    print("test_gates_on_named_inputs: OK")


def test_grouped_split_has_no_shared_family():
    clean = T.dedup(T.make_tickets())
    held = {f"{x}/0" for x in T.TYPES}
    tr, te = T.split_groups(clean, lambda t: t["family"], held)
    assert not ({t["family"] for t in tr} & {t["family"] for t in te})
    assert round(T.zero_fail_bound(105), 4) == 0.0286
    print("test_grouped_split_has_no_shared_family: OK")


def test_naive_bayes_learns():
    m = T.NaiveBayes().fit(["where is my parcel", "refund my money",
                            "where is order", "money back please"],
                           ["delivery", "refund", "delivery", "refund"])
    assert m.predict("where is it") == "delivery"
    assert m.predict("i want my money") == "refund"
    print("test_naive_bayes_learns: OK")


if __name__ == "__main__":
    test_no_ticket_in_two_splits()
    test_split_before_dedup_leaks()
    test_gates_on_named_inputs()
    test_grouped_split_has_no_shared_family()
    test_naive_bayes_learns()
