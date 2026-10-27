"""Chapter 12: scope is bound by the compiler; adversarial specs are refused."""
import _path  # noqa: F401

import structured as S
from access import Session

ASHA = Session("a", "asha", "customer", "IN")


def test_scope_always_bound_from_session():
    sql, params = S.compile_spec({"metric": "refund_total"}, ASHA)
    assert "tenant_id = ?" in sql and "customer_id = ?" in sql and params == ["a", "asha"]


def test_refund_count_this_year():
    assert S.ask("How many refunds did I get this year?", ASHA)[3] == [(1,)]


def test_same_name_other_tenant_not_visible():
    rows = S.ask("Which of my orders were final sale?", ASHA)[3]
    assert ("7001", "Trail shoes") not in rows


def test_every_adversarial_case_refused():
    for name, spec in S.ADVERSARIAL:
        try:
            S.compile_spec(spec, ASHA)
            raise AssertionError(name)
        except S.Refused:
            pass


def test_readonly_is_not_row_security():
    raw = "SELECT order_id FROM orders WHERE customer_id = 'asha' UNION SELECT order_id FROM orders"
    assert S.readonly_guard(raw) and len(S.db().execute(raw).fetchall()) == len(S.ORDERS)


if __name__ == "__main__":
    from _run import run_all
    run_all("test_structured")
