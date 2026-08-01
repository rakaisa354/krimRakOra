import pytest
from pdf_to_md import extract_rbl_transactions, rbl_pdf_text_to_md
from parsers.rbl import parse as parse_rbl

# Excerpt verbatim from pdf_decrypt.extract_text() output on a real decrypted
# RBL statement (dump/rbl/2026-04-16_..._135282877_15-04-2026.pdf). One
# transaction per line — no wrapping, unlike ICICI. The raw text drops the
# "CR" marker the PDF shows visually for payments/EMI transfers, and squashes
# the foreign-currency parenthetical against the preceding column.
RAW_EXCERPT = """
Date Description Amount /uni20B9
16 Mar 2026 PAYMENT UPI 19,011.00
16 Mar 2026 RAZ*TOUCHMYTOWN ECOM P http://www.to IND 468.00
16 Mar 2026 GOOGLEPLAY             MUMBAI        MAH 399.00
18 Mar 2026 PAYMENT UPI 5,000.00
25 Mar 2026 PADDLE.NET* N8N CLOUD1 London        GBR( EUR 16.10 ) 1,759.83
10 Apr 2026 TRANSFERRED TO EMI(SPLIT N PAY-12MTH) 10,713.40
13 Apr 2026 20% Cashback for SnP Proc Fee CB  Rs 100 100.00
7 Apr 2026 OPENAI *CHATGPT SUBSCR SAN FRANCISCO CA( USD 23.60 ) 2,199.85
"""


def test_extract_returns_expected_row_count():
    rows = extract_rbl_transactions(RAW_EXCERPT)
    assert len(rows) == 8


def test_extract_marks_payment_as_credit():
    rows = extract_rbl_transactions(RAW_EXCERPT)
    payment = next(r for r in rows if r["description"] == "PAYMENT UPI" and r["amount"] == "19,011.00")
    assert payment["is_credit"] is True


def test_extract_marks_regular_purchase_as_debit():
    rows = extract_rbl_transactions(RAW_EXCERPT)
    gplay = next(r for r in rows if "GOOGLEPLAY" in r["description"])
    assert gplay["is_credit"] is False


def test_extract_marks_emi_transfer_as_credit():
    rows = extract_rbl_transactions(RAW_EXCERPT)
    emi = next(r for r in rows if "TRANSFERRED TO EMI" in r["description"])
    assert emi["is_credit"] is True


def test_extract_marks_cashback_as_credit():
    rows = extract_rbl_transactions(RAW_EXCERPT)
    cashback = next(r for r in rows if "Cashback" in r["description"])
    assert cashback["is_credit"] is True


def test_extract_normalizes_foreign_currency_parenthetical():
    rows = extract_rbl_transactions(RAW_EXCERPT)
    n8n = next(r for r in rows if "N8N" in r["description"])
    assert "(EUR 16.10)" in n8n["description"]
    openai = next(r for r in rows if "OPENAI" in r["description"])
    assert "(USD 23.60)" in openai["description"]


def test_output_feeds_existing_rbl_parser():
    md = rbl_pdf_text_to_md(RAW_EXCERPT)
    parsed = parse_rbl(md)
    assert len(parsed) == 8


def test_output_foreign_currency_parsed_correctly():
    md = rbl_pdf_text_to_md(RAW_EXCERPT)
    parsed = parse_rbl(md)
    n8n = next(r for r in parsed if "N8N" in r["merchant"])
    assert n8n["currency"] == "EUR"
    assert n8n["amount"] == pytest.approx(16.10, rel=1e-2)
    assert n8n["amount_inr"] == pytest.approx(1759.83)


def test_output_payment_is_negative_inr():
    md = rbl_pdf_text_to_md(RAW_EXCERPT)
    parsed = parse_rbl(md)
    payment = next(r for r in parsed if r["merchant"] == "PAYMENT UPI" and r["amount_inr"] == -19011.0)
    assert payment["currency"] == "INR"
