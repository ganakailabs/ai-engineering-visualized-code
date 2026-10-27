"""Capstone: one ticket through every Vol 3 knowledge stage, end to end.

Asha (tenant a, customer, IN) writes about her orders, a broken mug, the NW-550
and a clearance jacket. Each stage runs on its own chapter's fixture, with the
part of her ticket that stage handles, and the run stops if any stage fails:
  1. contract and route (Ch 1)       6. hybrid search, exact lane (Ch 7)
  2. ingest with stable ids (Ch 2)   7. rerank (Ch 8)
  3. table rows kept (Ch 3)          8. precedence (Ch 10)
  4. applies-filter (Ch 4)           9. pack and citation check (Ch 11)
  5. access filter (Ch 5)           10. the regression gate (Ch 16)
Stub model only; run from the repo root:  python3 vol3/capstone.py
"""
import _root  # noqa: F401

import access as A
import assemble as AS
import chunking as C
import gate as G
import hybrid as H
import ingest as I
import layout as L
import precedence as P
import rerank as R
import sources as S

ASHA = A.Session("a", "asha", "customer", "IN")


def stages():
    out = {}
    need, _ = S.classify("What did I pay for order #2001?")
    out["route"] = S.route(need)

    store, files = I.Store(), sorted(I.MANUALS.glob("*.txt"))
    try:
        I.ingest(files, store, crash_on=2, echo=False)
    except I.Crash:
        pass
    run = I.ingest(files, store, echo=False)
    out["ingest"] = (run["skipped"], run["retried"], len(store.chunks),
                     I.duplicates(list(store.chunks.values())), len(I.orphans(store)))

    out["layout"] = L.run(echo=False)["spotcheck"]
    r = C.answer_context("My mug arrived broken. What do I need to send?",
                         product="mug", region="IN", echo=False)
    out["applies"] = [k.split(":")[1] for k in r["kept"]]
    out["access"] = A.retrieve(A.Index(), ASHA, "damaged refund photo")
    out["search"] = H.search("the nw-550 won't pair")[:3]
    q = "how long do I have to return unused items"
    out["rerank"] = R.rerank(q, R.first_stage(q, 20), 5)
    out["precedence"] = P.precedence(["R1@2026-09-15", "ticket-8812"])
    pack, _ = AS.assemble(AS.EIGHT)
    action, reply = AS.answer("can I return my clearance jacket, "
                              "and do I need a photo?", pack)
    out["pack"] = (AS.validate_citations(reply, pack), action)
    out["gate"] = G.gate("baseline", "chunking_fixed")
    return out


def main():
    s = stages()
    print("1. route    " + "  ".join(f"{n}->{c}:{p}" for n, c, p in s["route"]))
    sk, rt, n, d, o = s["ingest"]
    print(f"2. ingest   crash on file 2; rerun skipped={sk} retried={rt} "
          f"chunks={n} duplicates={d} orphans={o}")
    ok, n = s["layout"]
    print(f"3. layout   table spotcheck={ok}/{n}")
    print(f"4. applies  kept={s['applies']}")
    print(f"5. access   context={s['access']}")
    print(f"6. search   top3={s['search']}")
    print(f"7. rerank   top5={s['rerank']}")
    kept, dropped, esc = s["precedence"]
    print(f"8. precede  kept={kept} dropped={[i for i, _ in dropped]} escalate={esc}")
    (ok, cited, unknown), action = s["pack"]
    print(f"9. pack     cited={cited} in pack={ok} -> {action}")
    g = s["gate"]
    print(f"10. gate    critical={g['critical'] or 'none'} "
          f"answered={g['answered']}/{g['answerable']} -> {g['verdict']}")


if __name__ == "__main__":
    main()
