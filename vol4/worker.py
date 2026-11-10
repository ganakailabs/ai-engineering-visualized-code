"""A worker process for the Chapter 1 lab.

    python3 vol4/worker.py QUEUE_DB JOB_ID NAME [--hang-after-payment]

--hang-after-payment stops the worker after the payment lands and before the ledger
records it: the worst moment to die. The lab then kills it with SIGKILL, so no
except or finally block runs.
"""
import json
import sys
import time

import _root  # noqa: F401

from service import Queue, run_job


def main():
    path, job_id, name = sys.argv[1:4]
    hang = "--hang-after-payment" in sys.argv
    q = Queue(path)
    claim = q.lease(name, job_id)
    if not claim:
        print(json.dumps({"worker": name, "lease": "refused"}), flush=True)
        return
    print(json.dumps({"worker": name, "lease": "ok", "claim": claim}), flush=True)

    def stop_here():
        print(json.dumps({"worker": name, "paid": True}), flush=True)
        while True:
            time.sleep(1)                     # waits to be killed

    result = run_job(q, name, job_id, claim, on_payment=stop_here if hang else None)
    print(json.dumps({"worker": name, **result}), flush=True)


if __name__ == "__main__":
    main()
