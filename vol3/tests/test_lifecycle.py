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


if __name__ == "__main__":
    from _run import run_all
    run_all("test_lifecycle")
