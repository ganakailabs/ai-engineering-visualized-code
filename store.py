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
