import pytest
from parsers.sbi import parse

SAMPLE_MD = """# SBI Card Credit Card Statement
**Statement Period:** 11 Apr 2026 to 10 May 2026

## Transactions (11 Apr 2026 to 10 May 2026)

| Date | Transaction Details | Amount (₹) |
|---|---|---|
| 11 Apr 26 | PAYMENT RECEIVED 000DP21610155 | 13,911.19 C |
| 10 May 26 | FP EMI 05/12 (EXCL TAX 81.38) | 3,342.44 M |
| 10 May 26 | INTEREST ON EMI | 452.13 D |
| 26 Apr 26 | #GROUNDED CAFE, CHENNAI IN | 756.00 D |
| 23 Apr 26 | TRANSFER TO FLEXIPAY INSTALLMENT | 27,275.00 |
"""

def test_parse_debits_are_positive():
    rows = parse(SAMPLE_MD)
    cafe = next(r for r in rows if "GROUNDED" in r["merchant"])
    assert cafe["amount"] > 0

def test_parse_credits_are_negative():
    rows = parse(SAMPLE_MD)
    payment = next(r for r in rows if "PAYMENT" in r["merchant"])
    assert payment["amount"] < 0

def test_parse_emi_rows_tagged():
    rows = parse(SAMPLE_MD)
    emi = next(r for r in rows if "FP EMI" in r["merchant"])
    assert emi["payment_method"] == "emi"

def test_parse_date_format():
    rows = parse(SAMPLE_MD)
    cafe = next(r for r in rows if "GROUNDED" in r["merchant"])
    assert cafe["date"] == "2026-04-26"

def test_parse_sets_card_account():
    rows = parse(SAMPLE_MD)
    assert all(r["card_account"] == "SBI Card" for r in rows)

def test_parse_strips_hash_prefix():
    rows = parse(SAMPLE_MD)
    cafe = next(r for r in rows if "GROUNDED" in r["merchant"])
    assert not cafe["merchant"].startswith("#")

def test_parse_output_schema():
    rows = parse(SAMPLE_MD)
    required_keys = ["date","card_account","merchant","amount","currency",
                     "exchange_rate","amount_inr","category","subcategory",
                     "budget_type","payment_method","notes"]
    for row in rows:
        for key in required_keys:
            assert key in row, f"Missing key: {key}"
