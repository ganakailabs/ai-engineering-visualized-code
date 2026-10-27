"""Structured knowledge: QuerySpecs, mandatory scope and parameterized SQL (Vol 3 Ch 12).

The model never writes SQL. It fills a QuerySpec (metric, filters, year) from an
allow-list; compile_spec() turns it into parameterized SQL and binds tenant_id and
customer_id from the Session, on every query. Anything outside the allow-list is refused.
Fixture: SQLite in memory; Asha (tenant a) owns Vol 1's orders 1234, 2001, 3100, 4410.
"""
import re
import sqlite3

import _root  # noqa: F401

import llm
from access import Session

ORDERS = [  # order_id, tenant, customer, item, amount, delivered, final_sale
    ("1234", "a", "asha", "Desk lamp", 1800, "2026-08-24", 0),
    ("2001", "a", "asha", "Ceramic mug set", 950, "2026-10-01", 0),
    ("3100", "a", "asha", "Noise-cancelling headphones", 12500, "2026-09-28", 0),
    ("4410", "a", "asha", "Clearance jacket", 2200, "2026-09-30", 1),
    ("5120", "a", "ravi", "Wool scarf", 700, "2026-07-11", 1),
    ("5121", "a", "ravi", "Desk lamp", 1800, "2026-02-03", 0),
    ("7001", "b", "asha", "Trail shoes", 5400, "2026-05-19", 1),    # same name, other store
]
REFUNDS = [  # refund_id, order_id, tenant, customer, amount, refunded_on
    ("rf-1", "2001", "a", "asha", 950, "2026-10-02"),
    ("rf-2", "1234", "a", "asha", 1800, "2025-12-20"),
    ("rf-3", "5121", "a", "ravi", 1800, "2026-02-20"),
    ("rf-4", "7001", "b", "asha", 5400, "2026-06-01"),
]

METRICS = {   # metric -> (table, select expression, date column)
    "refund_count": ("refunds", "COUNT(*)", "refunded_on"),
    "refund_total": ("refunds", "COALESCE(SUM(amount), 0)", "refunded_on"),
    "order_list": ("orders", "order_id, item", "delivered"),
}
FILTERS = {"final_sale": ("orders", "final_sale = ?")}
SPEC_KEYS = {"metric", "year", "filters"}


def db():
    c = sqlite3.connect(":memory:")
    c.execute("CREATE TABLE orders (order_id, tenant_id, customer_id, item, amount, delivered, final_sale)")
    c.execute("CREATE TABLE refunds (refund_id, order_id, tenant_id, customer_id, amount, refunded_on)")
    c.executemany("INSERT INTO orders VALUES (?,?,?,?,?,?,?)", ORDERS)
    c.executemany("INSERT INTO refunds VALUES (?,?,?,?,?,?)", REFUNDS)
    return c


ADVERSARIAL = [
    ("union across customers", {"metric": "order_list UNION SELECT order_id, item FROM orders"}),
    ("join to another table", {"metric": "order_list", "join": "refunds"}),
    ("nested query in a filter", {"metric": "order_list", "filters": {"final_sale": "1 OR 1=1"}}),
    ("aggregate across tenants", {"metric": "refund_total", "group_by": "tenant_id"}),
    ("scope asked for in the spec", {"metric": "refund_count", "customer_id": "ravi"}),
]


class Refused(ValueError):
    pass


def validate(spec):
    extra = set(spec) - SPEC_KEYS
    if extra:
        raise Refused(f"field not allowed: {sorted(extra)}")
    if spec.get("metric") not in METRICS:
        raise Refused(f"metric not allowed: {spec.get('metric')!r}")
    year = spec.get("year")
    if year is not None and not (isinstance(year, int) and 2000 <= year <= 2100):
        raise Refused(f"year not allowed: {year!r}")
    for f, v in (spec.get("filters") or {}).items():
        if f not in FILTERS or FILTERS[f][0] != METRICS[spec["metric"]][0] or v not in (0, 1, True, False):
            raise Refused(f"filter not allowed: {f}={v!r}")


def compile_spec(spec, s: Session):
    """QuerySpec -> (sql, params). Scope is not optional and not taken from the spec."""
    validate(spec)
    table, select, date_col = METRICS[spec["metric"]]
    where, params = ["tenant_id = ?", "customer_id = ?"], [s.tenant_id, s.customer_id]
    if spec.get("year") is not None:
        where.append(f"substr({date_col}, 1, 4) = ?")
        params.append(str(spec["year"]))
    for f, v in (spec.get("filters") or {}).items():
        where.append(FILTERS[f][1])
        params.append(int(v))
    return f"SELECT {select} FROM {table} WHERE " + " AND ".join(where), params


SYSTEM = ("Fill a QuerySpec for the customer's question. Allowed keys: metric "
          "(refund_count, refund_total, order_list), year (int), filters ({final_sale: 0|1}). "
          'Reply as JSON: {"spec": {...}}. Never include customer or tenant fields.')


def _stub_spec(payload):
    """DEMONSTRATION spec writer, not a model: keyword rules for the chapter's questions."""
    q = payload.lower()
    if "final sale" in q:
        spec = {"metric": "order_list", "filters": {"final_sale": 1}}
    elif "how many refunds" in q:
        spec = {"metric": "refund_count", "year": 2026}
    else:
        spec = {"metric": "refund_total"}
    if re.search(r"everyone|all customers|grouped by customer", q):
        spec["group_by"] = "customer_id"           # what an injected request asks for
    return {"spec": spec}


def think(question):
    reply, _ = llm.ask_json(SYSTEM, question, _stub_spec)
    return (reply or {}).get("spec", {})


def ask(question, s: Session, conn=None):
    """Returns (spec, sql, params, rows) or raises Refused."""
    spec = think(question)
    sql, params = compile_spec(spec, s)
    rows = (conn or db()).execute(sql, params).fetchall()
    return spec, sql, params, rows


def readonly_guard(sql):
    """The BREAK: 'read-only' is necessary, not sufficient. This guard passes UNIONs."""
    return sql.lstrip().upper().startswith("SELECT") and ";" not in sql
