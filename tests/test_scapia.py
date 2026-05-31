import pytest
from parsers.scapia import parse

SAMPLE_MD = """# Scapia Federal Credit Card Statement
**Billing Cycle:** 25 Mar 2026 – 24 Apr 2026

## Transactions

| Date | Merchant | Amount (₹) | Coins |
|---|---|---|---|
| 25-03-2026 | Emelem Gourmet Llp | 236.00 | |
| 25-03-2026 | March'26 statement (Refund) | +26,578.71 | -1,135 |
| 27-03-2026 | Bill payment (Payment) | +10,000.00 | |
| 28-03-2026 | Zomato | 367.23 | |
"""

def test_parse_regular_transactions_positive():
    rows = parse(SAMPLE_MD)
    zomato = next(r for r in rows if r["merchant"] == "Zomato")
    assert zomato["amount"] > 0

def test_parse_refund_negative():
    rows = parse(SAMPLE_MD)
    refund = next(r for r in rows if "Refund" in r["merchant"])
    assert refund["amount"] < 0

def test_parse_payment_negative():
    rows = parse(SAMPLE_MD)
    payment = next(r for r in rows if "Payment" in r["merchant"])
    assert payment["amount"] < 0

def test_parse_coins_column_excluded():
    rows = parse(SAMPLE_MD)
    assert all("coins" not in r for r in rows)

def test_parse_date_format():
    rows = parse(SAMPLE_MD)
    zomato = next(r for r in rows if r["merchant"] == "Zomato")
    assert zomato["date"] == "2026-03-28"

def test_parse_sets_card_account():
    rows = parse(SAMPLE_MD)
    assert all(r["card_account"] == "Scapia Federal" for r in rows)

def test_parse_output_schema():
    rows = parse(SAMPLE_MD)
    required_keys = ["date","card_account","merchant","amount","currency",
                     "exchange_rate","amount_inr","category","subcategory",
                     "budget_type","payment_method","notes"]
    for row in rows:
        for key in required_keys:
            assert key in row, f"Missing key: {key}"
