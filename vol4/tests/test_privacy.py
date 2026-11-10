"""Implementation test for Chapter 14: tamper and truncation detected against the
checkpoint, restore plus the deletion journal, export lists every live store."""
import _path  # noqa: F401

import copy

import privacy as P

S = {"kind": "agent", "id": "s-1"}


def _log(n=12):
    safe = []
    log = P.AuditLog(safe, every=5)
    for i in range(n):
        log.append(S, "read_ticket", ticket=f"T-{i}")
    return log, safe


def test_tamper_detected():
    log, safe = _log()
    assert P.verify(log.rows, safe) == (True, "ok")
    bad = copy.deepcopy(log.rows)
    bad[6]["entry"]["ticket"] = "T-x"
    assert P.verify(bad, safe)[1] == "chain broken at entry 7"
    assert P.verify(P.rechain(bad), safe)[1] == "checkpoint 10 mismatch"
    print("test_tamper_detected: OK")


def test_truncation_detected_to_last_checkpoint():
    log, safe = _log()
    assert not P.verify(log.rows[:8], safe)[0]
    assert P.verify(log.rows[:11], safe)[0]     # after the last checkpoint: a gap
    print("test_truncation_detected_to_last_checkpoint: OK")


def test_rollback_needs_latest_expected():
    log, safe = _log()
    assert P.verify(log.rows[:7], safe[:1]) == (True, "ok")     # older valid state
    assert P.verify(log.rows[:7], safe[:1], latest_expected=10) == \
        (False, "rollback: checkpoint 10 not in the safe")
    assert P.verify(log.rows, safe, latest_expected=10) == (True, "ok")
    print("test_rollback_needs_latest_expected: OK")


def test_marker_gone_from_live_and_derived_stores():
    stores = P.fixture()
    snap, journal = P.backup(stores), []
    assert P.export(stores, "asha")["evals"] and P.export(stores, "asha")["train"]
    P.delete(stores, "asha", journal)
    again = P.restore(snap, journal)
    hits = [r for st in P.LIVE for r in again[st] if "mug" in r["text"]
            and r["customer"] == "asha"]
    assert hits == [] and not P.present(again, "asha")
    assert again["cache"] == stores["cache"]            # general answers stay
    print("test_marker_gone_from_live_and_derived_stores: OK")


def test_actor_from_session():
    log, _ = _log(1)
    e = log.append(S, "issue_refund", order="2001", actor="staff(meera)")
    assert e["actor"] == "agent(s-1)"
    print("test_actor_from_session: OK")


def test_restore_replays_journal():
    stores = P.fixture()
    snap, journal = P.backup(stores), []
    P.delete(stores, "asha", journal)
    assert not P.present(stores, "asha")
    assert P.present(P.restore(snap), "asha")
    fixed = P.restore(snap, journal)
    assert not P.present(fixed, "asha") and P.present(fixed, "ravi")
    print("test_restore_replays_journal: OK")


def test_export_lists_every_live_store():
    assert set(P.export(P.fixture(), "asha")) == set(P.LIVE)
    assert set(P.LIVE) <= set(P.DATA_MAP)
    print("test_export_lists_every_live_store: OK")


if __name__ == "__main__":
    test_tamper_detected()
    test_truncation_detected_to_last_checkpoint()
    test_rollback_needs_latest_expected()
    test_marker_gone_from_live_and_derived_stores()
    test_actor_from_session()
    test_restore_replays_journal()
    test_export_lists_every_live_store()
