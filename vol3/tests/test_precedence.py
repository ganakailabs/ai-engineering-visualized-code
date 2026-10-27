"""Chapter 10: four named conflicts, three dates kept apart, abstain floors."""
import _path  # noqa: F401

import precedence as P


def test_applicability_uses_effective_date_not_published():
    kept, dropped, _ = P.precedence(["R1@2026-09-15", "R1@2026-11-01", "R1-EU@2026-01-01"])
    assert kept == ["R1@2026-09-15"]
    assert ("R1@2026-11-01", "not yet effective") in dropped        # published today, not effective
    assert ("R1-EU@2026-01-01", "not applicable region") in dropped


def test_authority_beats_a_newer_ticket():
    kept, dropped, esc = P.precedence(["R1@2026-09-15", "ticket-8812"])
    assert kept == ["R1@2026-09-15"] and dropped == [("ticket-8812", "authority")] and not esc


def test_recency_only_among_peers():
    kept, dropped, _ = P.precedence(["R1@2026-06-01", "R1@2026-09-15"])
    assert kept == ["R1@2026-09-15"] and dropped == [("R1@2026-06-01", "superseded")]


def test_unresolved_conflict_escalates():
    kept, _, esc = P.precedence(["M7@2026-08-01a", "M7@2026-08-01b"])
    assert esc and kept == []


def test_floors_chosen_on_dev():
    assert {s: P.calibrate(s) for s in P.SCORES} == {"policy": 0.6, "manual": 0.65, "past_tickets": 0.85}
    assert P.outcome(P.SCORES["past_tickets"]["held"], 0.85) == (4, 4)


if __name__ == "__main__":
    from _run import run_all
    run_all("test_precedence")
