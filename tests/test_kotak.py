import pytest
from parsers.kotak import parse

SAMPLE_MD = """# Kotak Mahindra Bank Credit Card Statement
**Billing Date:** 05-Jun-2026

## Transactions

| Date | Description | Amount (₹) |
|---|---|---|
| 18-May-2026 | FOOD BARN INDIA PRIVAT | 4,277.00 |
| 20-May-2026 | THAI BEACH RESORT | 2,800.00 |
| 04-Jun-2026 | GST | 114.39 |
| 04-Jun-2026 | PAYMENT RECEIVED | 5,000.00 Cr |
"""

def test_parse_returns_list_of_dicts():
    rows = parse(SAMPLE_MD)
    assert isinstance(rows, list)
    assert len(rows) > 0

def test_parse_cr_suffix_is_negative():
    rows = parse(SAMPLE_MD)
    payment = next(r for r in rows if "PAYMENT" in r["merchant"])
    assert payment["amount"] < 0
    assert payment["amount_inr"] == pytest.approx(-5000.0)

def test_parse_plain_debit_is_positive():
    rows = parse(SAMPLE_MD)
    grocery = next(r for r in rows if "FOOD BARN" in r["merchant"])
    assert grocery["amount"] == pytest.approx(4277.0)
    assert grocery["amount_inr"] == pytest.approx(4277.0)

def test_parse_currency_is_always_inr():
    rows = parse(SAMPLE_MD)
    assert all(r["currency"] == "INR" for r in rows)
    assert all(r["exchange_rate"] == 1.0 for r in rows)

def test_parse_date_format():
    rows = parse(SAMPLE_MD)
    grocery = next(r for r in rows if "FOOD BARN" in r["merchant"])
    assert grocery["date"] == "2026-05-18"

def test_parse_sets_card_account():
    rows = parse(SAMPLE_MD)
    assert all(r["card_account"] == "Kotak Mahindra Bank" for r in rows)

def test_parse_output_schema():
    rows = parse(SAMPLE_MD)
    required_keys = ["date", "card_account", "merchant", "amount", "currency",
                      "exchange_rate", "amount_inr", "category", "subcategory",
                      "budget_type", "payment_method", "notes"]
    for row in rows:
        for key in required_keys:
            assert key in row, f"Missing key: {key}"
