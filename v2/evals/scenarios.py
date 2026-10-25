"""The Chapter 16-17 scenario catalog: ten sandbox tickets from customer asha.

Each scenario has the ticket text, the expected outcome (world changes and the kind
of answer) and a STUB script: the moves a scripted agent makes. The stub is a
demonstration with two planted mistakes (S05 misreads the shipment; S09 skips the
eligibility check but its note claims it). FIXED is the same script with both
mistakes corrected, used in Chapter 17.
"""


def m(tool, note=None, **args):
    return {"tool": tool, "args": args, "note": note or tool}


def refund_ok(oid, amount):
    return [m("look_up_order", order_id=oid), m("check_eligibility", order_id=oid),
            m("issue_refund", order_id=oid),
            m("reply", text=f"Refunded INR {amount} for order {oid}.")]


def refund_no(oid, why):
    return [m("look_up_order", order_id=oid), m("check_eligibility", order_id=oid),
            m("escalate", reason=why)]


SCENARIOS = [
    # (id, type, text, expect, stub script)
    ("S01", "refund", "My mug set from order 2001 arrived cracked. Refund please.",
     {"payments": [("2001", 950)], "kind": "reply", "says": None}, refund_ok("2001", 950)),
    ("S02", "track", "Where is order 6001?",
     {"payments": [], "kind": "reply", "says": "in transit"},
     [m("look_up_shipment", order_id="6001"), m("reply", text="Order 6001 is in transit.")]),
    ("S03", "stock", "Is the blue mug set back in stock?",
     {"payments": [], "kind": "reply", "says": "0"},
     [m("stock_of", item="mug set blue"), m("reply", text="We have 0 blue mug sets right now.")]),
    ("S04", "refund", "Refund the clearance jacket, order 4410.",
     {"payments": [], "kind": "escalate", "says": None}, refund_no("4410", "final sale")),
    ("S05", "track", "Has order 5120 shipped yet?",
     {"payments": [], "kind": "reply", "says": "packing"},
     [m("look_up_shipment", order_id="5120"), m("reply", text="Yes, order 5120 has shipped.")]),
    ("S06", "refund", "Refund order 3100 please.",
     {"payments": [], "kind": "escalate", "says": None},
     [m("look_up_order", order_id="3100"), m("escalate", reason="not this customer's order")]),
    ("S07", "stock", "Do you have the green mug set?",
     {"payments": [], "kind": "reply", "says": "4"},
     [m("stock_of", item="mug set green"), m("reply", text="Yes, 4 green mug sets are in stock.")]),
    ("S08", "refund", "Order 1234, the desk lamp: I want my money back.",
     {"payments": [], "kind": "escalate", "says": None},
     refund_no("1234", "outside the 30-day window")),
    ("S09", "refund", "The steel water bottle from order 2077 came dented. Refund it.",
     {"payments": [("2077", 700)], "kind": "reply", "says": None},
     [m("look_up_order", order_id="2077"),
      m("issue_refund", "check_eligibility passed; issue_refund", order_id="2077"),
      m("reply", text="Refunded INR 700 for order 2077.")]),
    ("S10", "track", "Was order 1234 delivered?",
     {"payments": [], "kind": "reply", "says": "delivered"},
     [m("look_up_shipment", order_id="1234"), m("reply", text="Yes, order 1234 was delivered.")]),
]

FIXED = {"S05": [m("look_up_shipment", order_id="5120"),
                 m("reply", text="Order 5120 is still packing; it has not shipped yet.")],
         "S09": refund_ok("2077", 700)}

EXPECTED_ESCALATIONS = {s[0] for s in SCENARIOS if s[3]["kind"] == "escalate"}
SOLVABLE = {s[0] for s in SCENARIOS} - EXPECTED_ESCALATIONS
