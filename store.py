"""Fictional store data for the book (Northwind Goods). Not real policy advice."""
from datetime import date

STORE_NAME = "Northwind Goods"  # fictional online store used throughout the book

TODAY = date(2026, 10, 4)  # pinned so examples are repeatable

POLICY = {
    "R1": "Unused items can be refunded within 30 days of delivery.",
    "R2": "Damaged items can be refunded or replaced within 7 days of delivery, with a photo.",
    "R3": "Final-sale items cannot be refunded.",
    "R4": "Refunds above INR 5,000 need a human agent's approval.",
}
POLICY_VERSION = "2026-09-15"

ORDERS = {
    "1234": {"item": "Desk lamp", "amount": 1800, "delivered": date(2026, 8, 24),
             "final_sale": False, "damaged": False},
    "2001": {"item": "Ceramic mug set", "amount": 950, "delivered": date(2026, 10, 1),
             "final_sale": False, "damaged": True},
    "3100": {"item": "Noise-cancelling headphones", "amount": 12500, "delivered": date(2026, 9, 28),
             "final_sale": False, "damaged": False},
    "4410": {"item": "Clearance jacket", "amount": 2200, "delivered": date(2026, 9, 30),
             "final_sale": True, "damaged": False},
}


def policy_text() -> str:
    lines = [f"POLICY (version {POLICY_VERSION}):"]
    lines += [f"[{cid}] {text}" for cid, text in POLICY.items()]
    return "\n".join(lines)


def fetch_order(order_id):
    return ORDERS.get(order_id)


# Ch 13-17: the help-centre handbook. The four refund clauses plus other pages.
# Ids: R1-R4 are the refund clauses; S1-S5 are other handbook passages.
HANDBOOK = dict(POLICY)
HANDBOOK.update({
    "S1": "Orders usually arrive within 5 business days. Track your parcel from the link in the shipping email.",
    "S2": "NW-500 headphones carry a 12-month warranty against defects. A battery that stops charging counts as a defect.",
    "S3": "Return shipping is free for damaged items. For other returns the customer pays return shipping.",
    "S4": "Gift cards cannot be exchanged for cash.",
    "S5": "Customers in the EU may withdraw from an online purchase within 14 days of delivery, without giving a reason.",
})
# Ch 14: labels on every passage (which customers it applies to)
REGION = {cid: "ALL" for cid in HANDBOOK}
REGION["S5"] = "EU"

# Ch 14: the same handbook as one long page of text, the way it arrives from the help centre
HANDBOOK_TEXT = " ".join(HANDBOOK[c] for c in ("S1", "R1", "R2", "S3", "R3", "R4", "S2", "S4", "S5"))

# Ch 19-22: shipments, stock and carriers for the agent chapters (fictional)
SHIPMENTS = {"5120": "packing", "6001": "in transit", "1234": "delivered"}
CARRIER_REDIRECT = {"6001": False}           # this carrier cannot redirect parcels
STOCK = {"mug set green": 4, "mug set blue": 0}

# Ch 23: one customer record, to show what should not leave your building
CUSTOMERS = {"asha": {"name": "Asha Rao", "email": "asha.rao@example.com",
                      "phone": "+91 98765 43210", "city": "Pune"}}
