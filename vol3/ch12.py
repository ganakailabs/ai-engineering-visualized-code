"""Chapter 12: Structured Knowledge: Query Specs, Scope and Safe SQL.

Run from the repo root:  python3 vol3/ch12.py
The model (a stub unless AIEV_MODEL is set) fills a QuerySpec; code compiles it to
parameterized SQL with the asker's scope bound from the session. Then the BREAK: a
read-only guard lets a UNION read everyone's orders. Then adversarial specs.
"""
import _root  # noqa: F401

import structured as S
from access import Session

ASHA = Session("a", "asha", "customer", "IN")


if __name__ == "__main__":
    conn = S.db()
    print("Part 1 (MM-085): question to query")
    spec, sql, params, rows = S.ask("How many refunds did I get this year?", ASHA, conn)
    print(f"  think  queryspec metric={spec['metric']} range={spec['year']}")
    print(f"  sql    {sql}")
    print(f"  check  scope customer={params[1]} tenant={params[0]} bound")
    print(f"  act    rows={rows}")
    print(f"  reply  You had {rows[0][0]} refund in {spec['year']}.")

    print("\nPart 2 (MM-169): scope before you query")
    raw = ("SELECT order_id, item FROM orders WHERE customer_id = 'asha' "
           "UNION SELECT order_id, item FROM orders")
    leaked = conn.execute(raw).fetchall() if S.readonly_guard(raw) else []
    print(f"  break  read-only guard passed={S.readonly_guard(raw)} rows={len(leaked)} "
          f"of {len(S.ORDERS)}, asha's in tenant a: 4")
    for name, spec in S.ADVERSARIAL:
        try:
            S.compile_spec(spec, ASHA)
            print(f"  adversarial  {name} -> compiled")
        except S.Refused as e:
            print(f"  adversarial  {name} -> refused ({str(e).split(":")[0]})")
