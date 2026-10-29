"""Chapter 14: content, access and delete sync; consistency; build, check, switch."""
import _path  # noqa: F401

import lifecycle as L


def fresh():
    src = L.sources()
    return src, L.build(src, "INDEX v1", "gram-v1")


def test_content_change_reembedded():
    src, ix = fresh()
    src["ret-30"].update(text="unused items refund within 14 days", version=2)
    assert L.sync(src, ix)["changed"] == 1 and ix.rows["ret-30"]["version"] == 2


def test_permission_only_change_caught_by_access_hash():
    src, ix = fresh()
    src["nw550-batt"]["audience"] = "internal"
    assert L.content_only_sync(src, ix) == 0
    assert L.sync(src, ix)["access_changed"] == 1
    assert "nw550-batt" not in ix.search("NW-550 battery replacement", k=12)


def test_delete_tombstoned_and_consistent():
    src, ix = fresh()
    del src["acct-pw"]
    assert L.sync(src, ix)["removed"] == 1 and "acct-pw" in ix.tombstones
    assert L.check(src, ix) == dict(orphans=0, stale=0, missing=0, mixed=False)


def test_half_built_and_mixed_refused_complete_switched():
    src, live = fresh()
    half = L.build(dict(list(src.items())[:6]), "v2", "gram-v2")
    assert L.switch(live, half, src)[0] is live
    mixed = L.build(src, "v2", "gram-v2")
    mixed.rows["ret-30"] = dict(live.rows["ret-30"])
    assert L.switch(live, mixed, src)[0] is live
    full = L.build(src, "v2", "gram-v2")
    assert L.switch(live, full, src)[0] is full


def test_version_only_change_synced_and_checked():
    # Review probe: same text and audience, new version number.
    src, ix = fresh()
    src["ret-30"]["version"] = 2
    assert L.check(src, ix)["stale"] == 1
    s = L.sync(src, ix)
    assert s["version_changed"] == 1 and s["changed"] == 0 and s["access_changed"] == 0
    assert ix.rows["ret-30"]["version"] == 2 and L.check(src, ix)["stale"] == 0


def test_partial_listing_never_tombstones():
    # Review probe: a source API returned half the documents.
    src, ix = fresh()
    partial = dict(list(src.items())[:6])
    s = L.sync(partial, ix, complete=False)
    assert s["removed"] == 0 and s["unlisted"] == len(src) - 6 and not ix.tombstones
    assert len(ix.rows) == len(src)
    s = L.sync(src, ix)                      # the next full listing finds nothing missing
    assert s["removed"] == 0


def test_complete_listing_still_tombstones():
    src, ix = fresh()
    del src["acct-pw"]
    assert L.sync(src, ix, complete=True)["removed"] == 1


if __name__ == "__main__":
    from _run import run_all
    run_all("test_lifecycle")
