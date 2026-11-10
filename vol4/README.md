# AI Engineering Visualized, Vol 4: companion code (`vol4/`)

`vol4/` is the companion code for **AI Engineering Visualized, Volume 4: Production AI**
(A Visual Guide to Shipping, Scaling and Securing AI Apps). It keeps running the same
Northwind Goods support assistant and puts it into production shape: an API and a job
queue with leased workers, service-level objectives and error budgets, and traces and
logs. It reuses Vol 3, Vol 2 and Vol 1 (`../vol3/`, `../vol2/`, `../vol1/`) unchanged;
`_root.py` puts them on the import path, so keep the four folders together (or set
`AIEV_CODE` to the folder that holds them). Python 3.10+, standard library only; the
stub model is the default.

**Status (Nov 2026):** Chapters 1-16 have code, exercise solutions and stub tests;
`run_solutions.py` ends with "all passed". The book edition prints tag `vol4-ed1`. Each chapter's code is a teaching fixture:
one mechanism on a small fictional dataset, not a production component. Traffic,
durations, dropped spans, live scores, experiment outcomes, canary results, routing
scores, attacks, incidents and the capstone weeks are simulated or scripted and
labelled so in the output; the CI case results in Chapter 6 are scripted.

## Start here

From the repo root:

    python3 vol4/ch01.py               # one chapter
    python3 vol4/run_solutions.py      # every Vol 4 solution and test; ends with "all passed"

**Network.** Needed only for `git clone` and `pip install -r requirements.txt`. Every
lab, solution and test then runs with no network: Chapter 1's server binds `127.0.0.1`
only and the model is a stub. **Tested on Linux** for `vol4-ed1`. macOS, and Windows in
PowerShell (`.venv\Scripts\Activate.ps1`, `python` for `python3`), should work but
have not been tested.

Optional: `pip install opentelemetry-proto` (checked with 1.45.2) and
`tests/test_otlp_proto.py` parses the Chapter 3 export with the official protobuf types;
without it the test reports SKIPPED.

| File | Chapter |
|---|---|
| `service.py`, `worker.py`, `lab.py`, `ch01.py` | Ch 1: API (`POST /tickets`, session identity), SQLite job queue with leases and a fenced complete, a worker process killed mid-refund |
| `readiness.py`, `docs/` | Ch 1: release manifest, ADR, threat-model and data-map starters, the readiness check |
| `slo.json`, `traffic.py`, `slo.py`, `ch02.py` | Ch 2: SLO definitions, a simulated week, error budgets, invariants, the release policy |
| `trace.py`, `logsink.py`, `ch03.py` | Ch 3: span trees, W3C traceparent across the queue, OTLP/JSON export, completeness, a redacting log sink |
| `shadow.py`, `traffic.py` (`live()`), `ch04.py` | Ch 4: stratified shadow sampling off the reply path, counted grading failures, a pinned grader rechecked against human labels, Wilson intervals, per-slice drift watch |
| `feedback.py`, `experiment.py`, `ch05.py` | Ch 5: thumbs-down to reviewed cases (Vol 3 hash split), sticky A/B assignment, planned sample size, delayed outcomes, superiority by a margin, planned size checked by simulation, interval against the margin |
| `release.py`, `releases/`, `ch06.py` | Ch 6: release manifests, CI with Vol 3's gate on the scenario catalog, pinned and migrated checkpoints, canary, rollback that keeps deletions |
| `latency.py`, `ch07.py` | Ch 7: critical-path waterfall from spans, speeding up the wrong box, stream, parallelize and skip, first words vs tokens per second (simulated durations) |
| `stream.py`, `ch08.py` | Ch 8: stream contract (no decision before the final check), SSE events, reconnect and cancel, backpressure: workers needed and a queue limit (simulated) |
| `cost.py`, `ch09.py` | Ch 9: cost per resolved ticket, application caches scoped by versions, tenant and permissions with an access recheck on every hit, structured cacheability, stable-first prompt prefix test |
| `routing.py`, `ch10.py` | Ch 10: scorecard per route (interval, critical cases, cost per resolved ticket), untested fallback (BREAK), outage with a reserve and enforced timeout, a capacity drill (simulated) |
| `serving.py`, `ch11.py` | Ch 11: rent-or-own worksheet and break-even (example inputs), KV cache and weight memory for an example model shape; optional Ollama prefill/decode timing |
| `triage.py`, `ch12.py` | Ch 12: a naive Bayes triage student from teacher labels (simulated tickets), review, dedup and split, two gates |
| `security.py`, `ch13.py` | Ch 13: trust boundaries, an attack library on a gullible stub, held-out variants, per-channel coverage |
| `privacy.py`, `ch14.py` | Ch 14: data boundary map, anchored audit trail, export and delete across every store, restore with a deletion journal |
| `incident.py`, `ch15.py` | Ch 15: contain, triage by box, recover, reconcile the ledger, verify (simulated incident) |
| `capstone.py`, `capstone/`, `ch16.py`, `capstone_alternatives.py` | Ch 16 and the Capstone appendix: practice and sealed weeks (sealed by hash), decision record, three-window report, graduation checks and release policy printed apart, one change at a time |
| `drill.py` | Joined Drill appendix: a crash after payment and a restore, through the real queue, ledger, trace and file restore with a mock payment provider |
| `evidence/run_evidence.py`, `runs/evidence/` | Experiment Ledger appendix: local Ollama runs (timing, route classification, recorded attacks) with provenance; see `runs/evidence/README.md` |
| `docs/experiment-ledger.csv` | the editable experiment ledger |
| `solutions/` | exercise solutions, each ends with "chNN solution: OK" |
| `tests/` | implementation tests on the stub |
| `runs/` | saved output of each chapter (`chNN.out`) and the Chapter 3 trace export |
