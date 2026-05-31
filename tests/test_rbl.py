import pytest
from parsers.rbl import parse

SAMPLE_MD = """# RBL Bank Credit Card Statement
**Statement Period:** 16 Apr 2026 to 15 May 2026

## Transactions

| Date | Description | Amount (₹) |
|---|---|---|
| 16 Apr 2026 | PAYMENT UPI | 35,533.00 CR |
| 16 Apr 2026 | GOOGLEPLAY, MUMBAI MAH | 399.00 |
| 25 Apr 2026 | PADDLE.NET* N8N CLOUD1, London GBR (EUR 70.80) | 7,827.22 |
| 07 May 2026 | OPENAI *CHATGPT SUBSCR, SAN FRANCISCO CA (USD 23.60) | 2,227.98 |
"""

def test_parse_returns_list_of_dicts():
    rows = parse(SAMPLE_MD)
    assert isinstance(rows, list)
    assert len(rows) > 0

def test_parse_cr_suffix_is_negative():
    rows = parse(SAMPLE_MD)
    payment = next(r for r in rows if "PAYMENT" in r["merchant"])
    assert payment["amount"] < 0

def test_parse_foreign_currency_extracted():
    rows = parse(SAMPLE_MD)
    n8n = next(r for r in rows if "N8N" in r["merchant"])
    assert n8n["currency"] == "EUR"
    assert n8n["amount"] == pytest.approx(70.80, rel=1e-2)

def test_parse_usd_transaction():
    rows = parse(SAMPLE_MD)
    openai = next(r for r in rows if "OPENAI" in r["merchant"])
    assert openai["currency"] == "USD"
    assert openai["amount"] == pytest.approx(23.60, rel=1e-2)

def test_parse_inr_transaction_currency():
    rows = parse(SAMPLE_MD)
    gplay = next(r for r in rows if "GOOGLEPLAY" in r["merchant"])
    assert gplay["currency"] == "INR"
    assert gplay["amount"] == pytest.approx(399.0)

def test_parse_sets_amount_inr_for_foreign():
    rows = parse(SAMPLE_MD)
    n8n = next(r for r in rows if "N8N" in r["merchant"])
    assert n8n["amount_inr"] == pytest.approx(7827.22)

def test_parse_date_format():
    rows = parse(SAMPLE_MD)
    gplay = next(r for r in rows if "GOOGLEPLAY" in r["merchant"])
    assert gplay["date"] == "2026-04-16"

def test_parse_sets_card_account():
    rows = parse(SAMPLE_MD)
    assert all(r["card_account"] == "RBL Bank" for r in rows)

def test_parse_output_schema():
    rows = parse(SAMPLE_MD)
    required_keys = ["date","card_account","merchant","amount","currency",
                     "exchange_rate","amount_inr","category","subcategory",
                     "budget_type","payment_method","notes"]
    for row in rows:
        for key in required_keys:
            assert key in row, f"Missing key: {key}"
