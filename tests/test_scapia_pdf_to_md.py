import pytest
from pdf_to_md import extract_scapia_transactions, scapia_pdf_text_to_md
from parsers.scapia import parse as parse_scapia

# Excerpt verbatim from pdf_decrypt.extract_text() output on a real decrypted
# Scapia Federal statement (dump/scapia/2026-04-25_Scapia_April_2026_...pdf).
# PDF text extraction squashes spaces within a single text run (merchant
# names run together), wraps long merchant names onto their own line before
# the amount, and interleaves a repeated page-header block (name / masked
# card numbers / billing cycle) into the transaction list at every page
# break. "YourEMItransactions" is a separate section for EMI instalment
# breakdowns of already-counted spend and must not be picked up.
RAW_EXCERPT = """
YourTransactions
25-03-2026·10:49 EmelemGourmetLlp ₹236.00
25-03-2026·15:24 March'26statement Refund +₹26,578.71 -1,135
27-03-2026·14:14 Billpayment Payment +₹10,000.00
04-04-2026·20:25 Pym*giftawayMakatiCityPh
 ₹848.83
04-04-2026·21:45 Ding*Ding.comIe
 ₹5,039.97KRakesh
•XXXXXXXXXXXX9859
 •XXXXXXXXXXXX9337
BillingCycle
25Mar2026-24Apr2026
05-04-2026·00:45 BlissByAnju ₹1,620.00 81
19-04-2026·13:06 Zomato ₹794.14 40
YourEMItransactions
25-04-2026·00:00 IherbNetherlandsB.v.Iherb.comNl ₹1,814.65
 5/6
"""


def test_extract_returns_expected_row_count():
    rows = extract_scapia_transactions(RAW_EXCERPT)
    assert len(rows) == 7


def test_extract_excludes_emi_section():
    rows = extract_scapia_transactions(RAW_EXCERPT)
    assert not any("Iherb" in r["merchant"] for r in rows)


def test_extract_joins_wrapped_merchant_and_amount():
    rows = extract_scapia_transactions(RAW_EXCERPT)
    row = next(r for r in rows if "Pym" in r["merchant"])
    assert row["amount"] == "848.83"


def test_extract_ignores_page_header_bleed():
    rows = extract_scapia_transactions(RAW_EXCERPT)
    row = next(r for r in rows if "Ding" in r["merchant"] and r["amount"] == "5,039.97")
    assert "KRakesh" not in row["merchant"]
    assert "BillingCycle" not in row["merchant"]


def test_extract_marks_credit_with_plus_sign():
    rows = extract_scapia_transactions(RAW_EXCERPT)
    refund = next(r for r in rows if "Refund" in r["merchant"])
    assert refund["amount"].startswith("+")
    payment = next(r for r in rows if "Payment" in r["merchant"])
    assert payment["amount"].startswith("+")


def test_extract_regular_purchase_has_no_sign():
    rows = extract_scapia_transactions(RAW_EXCERPT)
    zomato = next(r for r in rows if r["merchant"] == "Zomato")
    assert not zomato["amount"].startswith("+")


def test_output_feeds_existing_scapia_parser():
    md = scapia_pdf_text_to_md(RAW_EXCERPT)
    parsed = parse_scapia(md)
    assert len(parsed) == 7


def test_output_refund_and_payment_negative():
    md = scapia_pdf_text_to_md(RAW_EXCERPT)
    parsed = parse_scapia(md)
    refund = next(r for r in parsed if "Refund" in r["merchant"])
    assert refund["amount"] < 0
    payment = next(r for r in parsed if "Payment" in r["merchant"])
    assert payment["amount"] < 0


def test_output_regular_purchase_positive_with_date():
    md = scapia_pdf_text_to_md(RAW_EXCERPT)
    parsed = parse_scapia(md)
    zomato = next(r for r in parsed if r["merchant"] == "Zomato")
    assert zomato["amount"] == pytest.approx(794.14)
    assert zomato["date"] == "2026-04-19"
