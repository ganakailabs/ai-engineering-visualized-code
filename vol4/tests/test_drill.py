"""Joined drill: reconcile before resume records the payment; without it, safety rests
on the provider honouring the key; a restore rewinds claim numbers."""
import _path  # noqa: F401

import drill


def quiet(*a):
    pass


def test_reconcile_records_payment_without_calling():
    out = drill.run(reconcile=True, idempotent=False, echo=quiet)
    assert out["payments"] == 1 and out["replies"] == 1
    assert not out["stale_accepted"]


def test_idempotent_provider_absorbs_resume_without_reconcile():
    assert drill.run(reconcile=False, idempotent=True, echo=quiet)["payments"] == 1


def test_key_ignoring_provider_pays_twice_without_reconcile():
    assert drill.run(reconcile=False, idempotent=False, echo=quiet)["payments"] == 2


def test_restore_rewinds_claim_numbers():
    assert drill.run(echo=quiet)["claim_after_restore"] == 1


if __name__ == "__main__":
    test_reconcile_records_payment_without_calling()
    test_idempotent_provider_absorbs_resume_without_reconcile()
    test_key_ignoring_provider_pays_twice_without_reconcile()
    test_restore_rewinds_claim_numbers()
