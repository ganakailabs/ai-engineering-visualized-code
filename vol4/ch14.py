"""Chapter 14: Privacy, Governance and Data Lifecycle.

Run from the repo root:  python3 vol4/ch14.py
All stores and customers are SIMULATED (privacy.py). Part 1: the data map and an
export for Asha. Part 2: the audit trail, anchored to checkpoints in a separate safe;
an edit, a recomputed chain and a truncation, each detected. Part 3: delete everywhere,
then the BREAK (restore brings her back) and the FIX (replay the deletion journal).
Not legal advice; retention periods are placeholders.
"""
import _root  # noqa: F401

import copy

import privacy as P

AGENT = {"kind": "agent", "id": "s-a17"}
MEERA = {"kind": "staff", "id": "meera"}

if __name__ == "__main__":
    print("== Part 1: the data boundary map ==")
    print("the lab fixture's stores (yours will differ):")
    print(f"{'store':<9}{'holds':<28}{'erase':<8}retention")
    for s, (holds, how, keep) in P.DATA_MAP.items():
        print(f"{s:<9}{holds:<28}{how:<8}{keep}")
    stores = P.fixture()
    ex = P.export(stores, "asha")
    print("export asha: " + " ".join(f"{s}={n}" for s, n in ex.items()))
    print("  audit, journal: ids kept by policy, own access and retention")
    print("  provider: per product, dated; backups: listed by date")

    print("== Part 2: the audit trail ==")
    safe = []
    log = P.AuditLog(safe, every=5)
    e = log.append(AGENT, "issue_refund", order="2001", amount=40)
    print(f"audit append actor={e['actor']} action={e['action']} "
          f"order={e['order']}")
    for i in range(11):
        who = MEERA if i % 4 == 0 else AGENT
        log.append(who, "read_ticket", ticket=f"T-{100 + i}")
    print(f"audit entries={len(log.rows)} checkpoints in safe="
          f"{[s for s, _ in safe]}")
    ok, why = P.verify(log.rows, safe)
    print(f"audit verify vs checkpoint {why}")

    edited = copy.deepcopy(log.rows)
    edited[6]["entry"]["actor"] = "staff(someone-else)"
    ok, why = P.verify(edited, safe)
    print(f"edit entry 7 actor: audit verify FAILED {why}")
    ok, why = P.verify(P.rechain(edited), safe)
    print(f"edit + recompute chain: audit verify FAILED {why}")
    ok, why = P.verify(log.rows[:8], safe)
    print(f"truncated to 8 -> {'detected' if not ok else 'missed'}"
          f" ({why})")
    ok, why = P.verify(log.rows[:11], safe)
    print(f"truncated to 11 (after last checkpoint 10) -> "
          f"{'detected' if not ok else 'not detected'}")
    ok, why = P.verify(log.rows[:7], safe[:1])
    print(f"rollback: cut to 7, remove checkpoint 10 -> "
          f"{'detected' if not ok else 'not detected'}")
    ok, why = P.verify(log.rows[:7], safe[:1], latest_expected=10)
    print(f"  vs latest expected checkpoint 10, known elsewhere -> "
          f"{'detected' if not ok else 'not detected'}")

    print("== Part 3: delete, back up, restore ==")
    stores = P.fixture()
    nightly = P.backup(stores)                 # last night, before the delete
    journal = []
    d = P.delete(stores, "asha", journal)
    print(f"deleted chats={d['jobs']} replies={d['replies']} "
          f"memories={d['memory']} chunks={d['index']} logs={d['logs']}")
    print(f"  evals={d['evals']} train={d['train']} cache={d['cache']}")
    log.append(AGENT, "delete_customer", customer="asha")
    print(f"after delete asha present={'yes' if P.present(stores, 'asha') else 'no'}")
    broken = P.restore(nightly)
    print(f"BREAK restore only -> asha present="
          f"{'yes' if P.present(broken, 'asha') else 'no'} "
          f"memory={P.export(broken, 'asha')['memory']} "
          f"chunks={P.export(broken, 'asha')['index']}")
    fixed = P.restore(nightly, journal)
    print(f"restore + journal -> asha present="
          f"{'yes' if P.present(fixed, 'asha') else 'no'}")
    print(f"ravi kept: jobs={P.export(fixed, 'ravi')['jobs']}")
