"""Chapter 1: Production Architecture: APIs, Workers, State and Boundaries.

Run from the repo root:  python3 vol4/ch01.py
Starts the http.server API lab on 127.0.0.1 (a free port), posts Asha's ticket,
then runs real worker processes: one is killed with SIGKILL after the refund
payment lands and before the ledger records it; another resumes the job after the
lease runs out. The stub decides nothing here: the refund rule is code (R2).
A second case pauses a worker past its lease on an explicit clock: only the\ncurrent claim may complete. Fixture data is fictional. This is a lab, not a deployment (docs/adr-001.md).
"""
import _root  # noqa: F401

import lab
import readiness

if __name__ == "__main__":
    print("== Part 1: request path, job path (MM-147) ==")
    lab.kill_and_resume()
    print("\npause, expire, resume (a reused worker name):")
    lab.pause_expire_resume()
    print("\n== Part 2: the readiness map (MM-119) ==")
    for line in readiness.report(readiness.DOCS):
        print(line)
    print("\nwithout data-map.md and the queue owner (the Break):")
    for line in readiness.report(readiness.DOCS, drop=("data-map.md", "queue")):
        print(line)
