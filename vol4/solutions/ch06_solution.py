"""Chapter 6 exercise: Release a new embedder.

Ship a new embedding model (gram-v2, Vol 3's toy embedder) as release 16 while a job
that started on release 14 is still in flight. Predict first: what is the rollback
target, and which index does the in-flight job use?

A new embedder means a new index: vectors from two models are not comparable (Vol 3,
Chapter 14). Release 16a changes only the embedder and is blocked. Release 16 builds
INDEX 2026-11-04 with gram-v2 and runs Vol 3's Build, Check, Switch. The in-flight job
keeps its own release, so it reads its own index; the old index stays, because it is
the rollback target's index.
"""
import _path  # noqa: F401

import copy

import lifecycle as L                           # Vol 3 Ch 14
import release as R

src = L.sources()
indexes = {"2026-10-12": L.build(src, "INDEX 2026-10-12", "gram-v1")}
m14 = R.load("rel-14")
releases = {"rel-14": m14}

m16a = copy.deepcopy(m14)
m16a.update(release_id="rel-16a", rollback_target="rel-14")
m16a["versions"]["embedder"] = "gram-v2"
print("manifest rel-16a check:")
for p in R.check(m16a):
    head, _, tail = p.partition(": ")
    print(f"  {head}:\n    {tail}" if tail else f"  {p}")
assert any("build a new index" in p for p in R.check(m16a))

new = L.build(src, "INDEX 2026-11-04", "gram-v2")
live, why = L.switch(indexes["2026-10-12"], new, src)
print("build INDEX 2026-11-04 with gram-v2: check")
print("  " + ", ".join(f"{k}={v}" for k, v in L.check(src, new).items()))
print(f"  {why}")
indexes["2026-11-04"] = new
m16 = copy.deepcopy(m16a)
m16.update(release_id="rel-16", index_built_with="gram-v2",
           eval_report={"index_switch": why}, rollback_target="rel-14")
m16["versions"]["index"] = "2026-11-04"
releases["rel-16"] = m16
print(f"manifest rel-16 check: {R.check(m16) or 'complete'} "
      f"(index {m16['versions']['index']} + embedder {m16['versions']['embedder']})")

job = {"job_id": "op-a-T-2001-a", "release_id": "rel-14"}          # started on 14
own = releases[job["release_id"]]["versions"]["index"]
hit = indexes[own].search("my mug set arrived chipped")[0]
print(f"job={job['job_id']} pinned release=14")
print(f"  -> index {own} ({indexes[own].model}) top hit={hit}")
target = releases[m16["rollback_target"]]["versions"]["index"]
print(f"rollback target={m16['rollback_target']} -> index {target} kept")
print(f"  (indexes held: {', '.join(sorted(indexes))})")
assert own == "2026-10-12" and target in indexes and not R.check(m16)
print("ch06 solution: OK")
