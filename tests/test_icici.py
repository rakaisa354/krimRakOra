import pytest
from parsers.icici import parse

SAMPLE_MD = """# ICICI Bank - Amazon Pay Credit Card Statement
**Statement Period:** April 3, 2026 to May 2, 2026
**Card Number:** 4315XXXXXXXX4018

## Transactions

| Date | Ser No. | Transaction Details | Reward Points | Amount (₹) |
|---|---|---|---|---|
| 03/04/2026 | 13166192192 | Interest Amount Amortization - <24/24> ZOMATO LTD | 0 | 1.20 |
| 05/04/2026 | 13166192200 | ZOMATO ONLINE ORDER | 414 | 450.00 |
| 10/04/2026 | 13166192210 | PAYMENT RECEIVED | 0 | 5000.00 CR |
"""

def test_parse_returns_list_of_dicts():
    rows = parse(SAMPLE_MD)
    assert isinstance(rows, list)
    assert len(rows) > 0

def test_parse_excludes_amortization_rows():
    rows = parse(SAMPLE_MD)
    descriptions = [r["merchant"] for r in rows]
    assert not any("Amortization" in d for d in descriptions)

def test_parse_marks_credits_correctly():
    rows = parse(SAMPLE_MD)
    payment = next(r for r in rows if "PAYMENT" in r["merchant"])
    assert payment["amount"] < 0

def test_parse_normalizes_date_format():
    rows = parse(SAMPLE_MD)
    debit = next(r for r in rows if r["amount"] > 0)
    assert debit["date"] == "2026-04-05"

def test_parse_sets_card_account():
    rows = parse(SAMPLE_MD)
    assert all(r["card_account"] == "ICICI Amazon Pay" for r in rows)

def test_parse_sets_currency_inr():
    rows = parse(SAMPLE_MD)
    assert all(r["currency"] == "INR" for r in rows)

def test_parse_output_schema():
    rows = parse(SAMPLE_MD)
    required_keys = ["date","card_account","merchant","amount","currency",
                     "exchange_rate","amount_inr","category","subcategory",
                     "budget_type","payment_method","notes"]
    for row in rows:
        for key in required_keys:
            assert key in row, f"Missing key: {key}"
