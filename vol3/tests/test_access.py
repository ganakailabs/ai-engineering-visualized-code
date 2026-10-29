"""Chapter 5: no cross-tenant leak at any of the five doors; revocation; quarantine."""
import _path  # noqa: F401

import access as A

ASHA = A.Session("a", "asha", "customer", "IN")
AGENT_A = A.Session("a", "agent-7", "internal", "IN")
BEN_B = A.Session("b", "ben", "customer", "IN")      # same region, other tenant
Q = "damaged refund photo"


def test_search_door():
    ix = A.Index()
    assert all(ix.rows[c]["tenant"] == "a" for c in ix.search(ASHA, Q))
    assert "a-note.1" not in ix.search(ASHA, "escalate refunds")
    assert "a-note.1" in ix.search(AGENT_A, "escalate refunds")


def test_expand_door_parent_leak():
    ix = A.Index()
    assert "b-note.1" in ix.expand(ASHA, "a-ret.1", filtered=False)     # the Break
    assert "b-note.1" not in ix.expand(ASHA, "a-ret.1")


def test_rerank_and_cite_doors():
    ix = A.Index()
    assert ix.rerank_input(ASHA, ["a-ret.1", "b-ret.1"]) == ["a-ret.1"]
    assert not ix.cite_ok(ASHA, ["b-note.1"]) and ix.cite_ok(ASHA, ["a-ret.2"])


def test_cache_door_is_scoped_by_identity():
    ix = A.Index()
    A.retrieve(ix, ASHA, Q)
    assert ix.cached_answer(BEN_B, Q) is None
    assert ix.cache_key(ASHA, Q) != ix.cache_key(BEN_B, Q)
    assert all(ix.rows[c]["tenant"] == "b" for c in A.retrieve(ix, BEN_B, Q))


def test_revocation_next_query():
    ix = A.Index()
    A.retrieve(ix, ASHA, Q)
    ix.revoke("a-ret")
    assert A.retrieve(ix, ASHA, Q) == []


def test_quarantine_is_a_signal_with_a_miss():
    ix = A.Index()
    assert ix.ingest_supplier() == 1
    assert ix.quarantine == ["sup-1"] and "sup-2" in ix.rows    # the scripted miss
    assert "sup-2" not in ix.search(BEN_B, "NW-500 refund")     # boundary still holds


def test_cache_key_separates_regions():
    # Review probe: same customer, different region, must not share a cached answer.
    ix = A.Index()
    A.retrieve(ix, ASHA, Q)
    asha_eu = A.Session("a", "asha", "customer", "EU")
    assert ix.cache_key(ASHA, Q) != ix.cache_key(asha_eu, Q)
    assert ix.cached_answer(asha_eu, Q) is None


def test_cached_ids_refiltered_on_read():
    ix = A.Index()
    ix.cache[ix.cache_key(ASHA, Q)] = ["a-ret.1", "b-note.1"]   # a poisoned entry
    assert ix.cached_answer(ASHA, Q) == ["a-ret.1"]


if __name__ == "__main__":
    from _run import run_all
    run_all("test_access")
