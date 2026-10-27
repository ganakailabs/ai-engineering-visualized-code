"""Capstone: each stage's outcome, asserted on trusted state."""
import _path  # noqa: F401

import capstone


def test_every_stage():
    s = capstone.stages()
    assert s["route"] == [("order_fact", "orders", "lookup")]
    skipped, retried, n, dupes, orphans = s["ingest"]
    assert (skipped, retried, dupes, orphans) == (1, 1, 0, 0) and n == 12
    assert s["layout"] == (3, 3)
    assert s["applies"] == ["R1", "R2", "R3"]
    assert all(c.startswith("a-") for c in s["access"])
    assert "nw550-pair" in s["search"]
    assert "ret-window" in s["rerank"]
    kept, dropped, esc = s["precedence"]
    assert kept == ["R1@2026-09-15"] and not esc
    (ok, cited, unknown), action = s["pack"]
    assert ok and not unknown and action == "send"
    assert s["gate"]["verdict"] == "pass" and not s["gate"]["critical"]


if __name__ == "__main__":
    from _run import run_all
    run_all("test_capstone")
