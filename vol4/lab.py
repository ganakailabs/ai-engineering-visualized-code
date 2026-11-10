"""Chapter 1 lab driver: start the API, post a ticket, run, kill and resume workers.

Shared by ch01.py, the exercise solution and tests/test_kill.py, so all three run
the same real processes against the same SQLite file.
"""
import json
import os
import subprocess
import sys
import shutil
import tempfile
import time
import urllib.request
from pathlib import Path

import _root  # noqa: F401

import service

HERE = Path(__file__).resolve().parent
TICKET = {"ticket_id": "T-2001-a", "order_id": "2001",
          "text": "My mug set from #2001 arrived chipped. Photo attached. Refund please."}


def post(port, token, body):
    req = urllib.request.Request(f"http://127.0.0.1:{port}/tickets", method="POST",
                                 data=json.dumps(body).encode(),
                                 headers={"Authorization": f"Bearer {token}",
                                          "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


def spawn(path, job_id, name, hang=False):
    cmd = [sys.executable, str(HERE / "worker.py"), path, job_id, name]
    if hang:
        cmd.append("--hang-after-payment")
    env = dict(os.environ)
    return subprocess.Popen(cmd, stdout=subprocess.PIPE, text=True, env=env)


def read_line(proc):
    return json.loads(proc.stdout.readline())


def kill_and_resume(echo=print):
    """The whole Chapter 1 story. Returns the trusted state for assertions."""
    tmp = tempfile.mkdtemp(prefix="aiev-v4-ch01-")
    path = str(Path(tmp) / "queue.db")
    api = service.start_api(path)
    port = api.server_address[1]
    status, r = post(port, "s-asha", dict(TICKET, customer_id="c-42"))  # body id ignored
    job = r["job_id"]
    echo(f"api POST /tickets tenant={r['tenant_id']} caller={r['customer_id']} "
         f"-> {status} job={job}")
    status2, r2 = post(port, "s-asha", TICKET)                           # client retry
    echo(f"api POST /tickets (retry) -> {status2} job={r2['job_id']} "
         f"created={r2['created']}")
    status3, _ = post(port, "", TICKET)
    echo(f"api POST /tickets (no session) -> {status3}")

    w1 = spawn(path, job, "worker1", hang=True)
    first = read_line(w1)
    held = service.Queue(path).get(job)
    echo(f"worker1 lease job={job} {first['lease']} until=+{service.LEASE_S:.0f}s "
         f"(claim {first['claim']})")
    assert read_line(w1)["paid"]                     # payment landed, ledger not updated
    w2 = spawn(path, job, "worker2")
    echo(f"worker2 lease job={job} -> {read_line(w2)['lease']}")
    w2.wait()
    w1.kill()          # SIGKILL on Linux/macOS, TerminateProcess on Windows: no cleanup runs
    w1.wait()
    pays, reps = service.counts(path, job)
    echo(f"kill worker1 (SIGKILL) -> payments={pays} replies={reps}, "
         f"job {service.Queue(path).get(job)['state']}")
    time.sleep(service.LEASE_S + 0.5)                # wait out the lease
    echo("lease expired -> job free again")
    w3 = spawn(path, job, "worker2")
    lease = read_line(w3)["lease"]
    result = read_line(w3)
    w3.wait()
    pays, reps = service.counts(path, job)
    final = service.Queue(path).get(job)
    echo(f"worker2 lease job={job} -> {lease}")
    echo(f"worker2 ledger {result['ledger_before']} -> reconcile by key "
         f"-> {result['ledger_after']}")
    echo(f"worker2 payment calls: {result['payment_calls']}")
    echo(f"worker2 resume -> {result['state']} ({result['clause']})")
    echo(f"payments={pays} replies={reps} attempts={final['attempts']}")
    api.shutdown()
    return {"path": path, "job_id": job, "payments": pays, "replies": reps,
            "state": final["state"], "owner": final["owner"],
            "status": (status, status2, status3), "created": (r["created"], r2["created"]),
            "customer_id": r["customer_id"],
            "payment_calls_on_resume": result["payment_calls"]}


def pause_expire_resume(echo=print):
    """The hostile lease case, on an explicit clock (no sleeping): worker1 takes the
    job and pauses (a long GC pause, a frozen VM) past its lease. A restarted worker
    that reuses the name worker1 claims the job. The old worker1 wakes up and tries to
    finish. Only the current claim may complete. Returns the trusted state."""
    tmp = tempfile.mkdtemp(prefix="aiev-v4-ch01-pause-")
    q = service.Queue(str(Path(tmp) / "queue.db"))
    ident = service.SESSIONS["s-asha"]
    job = service.job_id_for(ident, "T-1234-a")
    q.enqueue(job, ident, "T-1234-a", {"order_id": "1234", "text": "where is it"})
    old = q.lease("worker1", job, now=100.0)
    echo(f"worker1 lease job={job} claim={old} at t=100.0,")
    echo(f"  then paused past its {service.LEASE_S:.0f}s lease")
    new = q.lease("worker1", job, now=103.5)
    echo(f"worker1 (restarted, same name) lease at t=103.5 -> claim={new}")
    late = q.complete("worker1", job, old, {"late": True}, now=104.0)
    echo(f"old worker1 wakes, complete claim={old} -> "
         f"{'DONE' if late else 'refused'} (current claim {new})")
    ok = q.complete("worker1", job, new, {"ok": True}, now=104.0)
    echo(f"new worker1 complete claim={new} -> {'DONE' if ok else 'refused'}")
    state = q.get(job)["state"]
    q.db.close()
    shutil.rmtree(tmp, ignore_errors=True)
    return {"old": old, "new": new, "late_done": late, "new_done": ok, "state": state}
