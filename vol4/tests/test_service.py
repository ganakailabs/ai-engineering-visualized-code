"""Implementation tests for Chapter 1: leases, the fence, idempotent enqueue, identity."""
import _path  # noqa: F401

import json
import tempfile
from pathlib import Path

import lab
import readiness
import service

ASHA = service.SESSIONS["s-asha"]
path = str(Path(tempfile.mkdtemp()) / "q.db")
q = service.Queue(path)

# idempotent enqueue: the job id is the operation id
jid = service.job_id_for(ASHA, "T-2001-a")
assert jid == "op-a-T-2001-a"
assert q.enqueue(jid, ASHA, "T-2001-a", {"order_id": "2001", "text": "x"}) is True
assert q.enqueue(jid, ASHA, "T-2001-a", {"order_id": "2001", "text": "x"}) is False

# leases on an explicit clock
assert q.lease("w1", jid, lease_s=3, now=100.0) == 1
assert not q.lease("w2", jid, lease_s=3, now=102.9)          # live lease: refused
assert q.lease("w2", jid, lease_s=3, now=103.0) == 2         # expired: free again
assert q.get(jid)["owner"] == "w2" and q.get(jid)["attempts"] == 2
assert not q.complete("w1", jid, 1, {}, now=103.5)           # fence: lost lease
assert not q.complete("w2", jid, 1, {}, now=103.5)           # fence: an old claim number
assert q.complete("w2", jid, 2, {"ok": 1}, now=103.5)
assert q.get(jid)["state"] == "DONE"
assert not q.lease("w3", jid, now=999.0)                     # DONE is never leased again

# the worker refuses an order the session's customer does not own (#3100 is c-42's)
other = service.job_id_for(ASHA, "T-3100-a")
q.enqueue(other, ASHA, "T-3100-a", {"order_id": "3100", "text": "refund"})
c = q.lease("w1", other, now=None)
assert c == 1
r = service.run_job(q, "w1", other, c)
assert r["clause"] == "not your order" and r["state"] == "DONE"
assert service.counts(path, other) == (0, 1)                 # no payment, one reply

# the API: identity from the session; no session is 401
api = service.start_api(path)
port = api.server_address[1]
status, body = lab.post(port, "s-asha", {"ticket_id": "T-1234-a", "order_id": "1234",
                                         "text": "where is it", "customer_id": "c-42"})
assert status == 202 and body["customer_id"] == "asha" and body["tenant_id"] == "a"
assert q.get("op-a-T-1234-a")["customer_id"] == "asha"
assert lab.post(port, "s-nobody", {"ticket_id": "T-9", "order_id": "1", "text": ""})[0] == 401
api.shutdown()

# MM-119: the readiness map
ticks = readiness.check(readiness.DOCS)
assert all(ticks.values()) and len(ticks) == 12
manifest = json.loads((readiness.DOCS / "release-manifest.json").read_text())
assert set(manifest["components"]) == {"api", "queue", "workers", "state", "providers",
                                       "knowledge", "tools", "secrets"}
broken = readiness.check(readiness.DOCS, drop=("data-map.md", "queue"))
assert [k for k, ok in broken.items() if not ok] == ["queue", "data-map.md"]
# a paused worker whose lease expired cannot complete, even with nobody else holding it
j3 = service.job_id_for(ASHA, "T-2001-x")
q.enqueue(j3, ASHA, "T-2001-x", {"order_id": "2001", "text": "x"})
c3 = q.lease("w1", j3, lease_s=3, now=200.0)
assert not q.complete("w1", j3, c3, {}, now=203.0)           # expired at 203.0
p = lab.pause_expire_resume(echo=lambda line: None)
assert (p["late_done"], p["new_done"]) == (False, True)
print("test_service: OK")
