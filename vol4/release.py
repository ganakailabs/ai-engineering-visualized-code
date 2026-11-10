"""Chapter 6: release engineering. Every change is a version you can take back.

MM-140 Everything Is a Version: a release manifest pins code, workflow, checkpoint
       schema, prompt, model, embedder, index, tools, evals and data, with the eval
       report and the rollback target. A job carries the release_id it started under,
       and its checkpoint carries its schema version.
MM-141 Canary and Rollback: a small sticky share of customers gets the new release;
       the Ch 5 comparison decides. Rollback is one switch of the live pointer. It
       does not restore old data (deletions stay deleted) and it cannot unsend a
       refund: those are listed for review, and any compensation is a new action.

The CI gate is Vol 3's gate_results() on the scenario catalog; the case results are
scripted (a release decision needs real, graded case outputs).
"""
import copy
import hashlib
import json
from pathlib import Path

import gate                                    # Vol 3 Ch 16

HERE = Path(__file__).resolve().parent
VERSIONS = ("code", "workflow", "checkpoint", "prompt", "model", "embedder", "index",
            "tools", "evals", "data")


def load(release_id):
    return json.loads((HERE / "releases" / f"{release_id}.json").read_text())


def check(m):
    """What stops a manifest from shipping: a missing version, no eval report, no
    rollback target, or an index built with a different embedder."""
    problems = [f"missing version: {k}" for k in VERSIONS if not m["versions"].get(k)]
    if not m.get("eval_report"):
        problems.append("missing eval_report")
    if not m.get("rollback_target"):
        problems.append("missing rollback_target")
    if m.get("index_built_with") != m["versions"].get("embedder"):
        problems.append(f"index {m['versions'].get('index')} built with "
                        f"{m.get('index_built_with')}, embedder is "
                        f"{m['versions'].get('embedder')}: build a new index")
    return problems


# ---------- CI: the series gate on the scenario catalog ----------

CATALOG = [  # (SC id, severity) from series/series-contract.md section 3.2
    ("SC-001", "critical"), ("SC-002", "critical"), ("SC-003", "critical"),
    ("SC-004", "major"), ("SC-005", "major"), ("SC-006", "major"), ("SC-007", "major"),
    ("SC-008", "critical"), ("SC-009", "major"), ("SC-010", "minor"),
    ("SC-011", "critical"), ("SC-012", "critical"), ("SC-013", "critical"),
    ("SC-014", "minor"), ("SC-015", "major"), ("SC-016", "major"), ("SC-017", "major"),
    ("SC-018", "major"), ("SC-019", "major"), ("SC-020", "critical")]
BENCH = [(sc, "catalog", True, sev == "critical") for sc, sev in CATALOG]
SCRIPTED_FAILS = {"prompt v7": set(), "prompt v8": {"SC-002"}, "prompt v8.1": set()}


def case_results(prompt):
    """Scripted per-case results {SC id: (correct, abstained)} for one prompt."""
    return {sc: (sc not in SCRIPTED_FAILS[prompt], False) for sc, _ in CATALOG}


def ci(base_prompt, new_prompt):
    return gate.gate_results(case_results(base_prompt), case_results(new_prompt), bench=BENCH)


# ---------- in-flight jobs and checkpoints ----------

def checkpoint(release_id, schema, done):
    """done: steps whose side effect happened. v2 keeps a list, v3 a dict."""
    if schema == "v2":
        return {"schema": "v2", "release_id": release_id, "ledger": sorted(done)}
    return {"schema": "v3", "release_id": release_id, "steps": {s: "SENT" for s in done}}


def migrate_v2_v3(ck):
    """The tested migration: every v2 ledger entry becomes a v3 step."""
    assert ck["schema"] == "v2"
    return {"schema": "v3", "release_id": ck["release_id"],
            "steps": {s: "SENT" for s in ck["ledger"]}}


def resume(ck, worker_schema, payments, step="refund-2001"):
    """A worker resumes a job: it skips steps its reading of the checkpoint says are
    done, then performs the rest. Returns the steps it saw as done."""
    done = set(ck.get("ledger", [])) if worker_schema == "v2" else set(ck.get("steps", {}))
    if step not in done:
        payments.append(step)
    return done


def route_job(job, live, revoked=frozenset()):
    """The release matrix for one job when `live` is the release now serving.
    job: {"release": id that started it, "effects": side effects already done?,
          "next_op": the tool operation it would run next}.
    Pinning code to the old release keeps the job's state readable; it does not
    authorize the next operation. Every next action is checked against today's
    authorization, so a revoked or unsafe next step pauses the job instead."""
    if job["release"] == live:
        return f"run on {live}"
    if not job["effects"]:
        return f"restart on {live}"
    if job["next_op"] in revoked:
        return "pause: next op revoked, keep state"
    return f"finish on {job['release']}, next action rechecked"


# ---------- canary and rollback ----------

def in_canary(customer, release_id, share=10):
    h = int(hashlib.sha256(f"canary:{release_id}:{customer}".encode()).hexdigest(), 16)
    return h % 100 < share


class Deploy:
    """The live pointer, the data store and the deletion log."""

    def __init__(self, live, data):
        self.live, self.data, self.deleted = live, data, []
        self.snapshots = {live: copy.deepcopy(data)}

    def ship(self, release_id):
        self.snapshots[release_id] = copy.deepcopy(self.data)
        self.live = release_id

    def delete(self, ids):
        for i in ids:
            self.data.pop(i, None)
            self.deleted.append(i)

    def rollback_naive(self, target):
        """Restore the target's snapshot: code AND data go back in time."""
        self.live, self.data = target, copy.deepcopy(self.snapshots[target])

    def rollback(self, target):
        """One switch of the pointer; data stays; the deletion log is re-applied."""
        self.live = target
        for i in self.deleted:
            self.data.pop(i, None)
        return sum(i not in self.data for i in self.deleted)
