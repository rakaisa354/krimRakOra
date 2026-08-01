import pytest
from pdf_to_md import extract_kotak_transactions, kotak_pdf_text_to_md
from parsers.kotak import parse as parse_kotak

# Excerpt verbatim from pdf_decrypt.extract_text() output on a real decrypted
# Kotak "Cashback+ Credit Card" statement
# (dump/kotak/2026-06-06_94XXXXXXXXXXX255_decrypted.pdf). One transaction
# per line.
#
# Every purchase here is tagged "(Convert To EMI)" and is reversed in the
# SAME statement by a matching "EMI CONV <merchant>(024) <same amount> Cr"
# line — net zero. Only the "EMI PRIN FOR ..." + "EMI INT-..." sub-lines are
# real new spend for this cycle: their sum (181.19+93.57+527.93+179.79 =
# 982.48) plus GST (114.39) is what should come out of this excerpt. THAI
# BEACH RESORT is included with no PRIN/INT lines on purpose, to prove an
# un-converted purchase (no matching "(Convert To EMI)" tag) still counts
# at face value.
RAW_EXCERPT = """Transactions Details from 06-May-2026 to 05-Jun-2026
Date Description Spends Category Amount (₹)
Purchases made in this cycle - Primary Card X8502
18-May-2026 FOOD BARN INDIA PRIVAT               356 (Convert To EMI) Grocery 4,277.00
20-May-2026 THAI BEACH RESORT                    356 Hotels 2,800.00
21-May-2026 RTRADERS                             356 (Convert To EMI) Fuel 10,273.82
EMI & Loans
24-May-2026 EMI CONV FOOD BARN INDIA PRIVAT(024) 4,277.00 Cr
24-May-2026 EMI PRIN FOR FOOD BARN INDIA (001/024) 181.19
24-May-2026 EMI INT-FOOD BARN INDIA PRIV (001/024) 93.57
24-May-2026 EMI CONV RTRADERS(024) 10,273.82 Cr
24-May-2026 EMI PRIN FOR RTRADERS (001/024) 527.93
24-May-2026 EMI INT-RTRADERS (001/024) 179.79
Total Purchases 2,782.48
Other fees and charges
04-Jun-2026 GST 114.39
Total Fees & Charges 114.39
GST applicable on interest, fee and charges. Foreclosure fee as applicable on loans. Page 2 of
4"""


def test_extract_returns_expected_row_count():
    rows = extract_kotak_transactions(RAW_EXCERPT)
    # THAI BEACH RESORT (uncoverted purchase) + 2x(PRIN+INT) + GST = 6
    assert len(rows) == 6


def test_extract_excludes_converted_purchase_and_its_reversal():
    rows = extract_kotak_transactions(RAW_EXCERPT)
    assert not any(r["description"] == "FOOD BARN INDIA PRIVAT" for r in rows)
    assert not any("EMI CONV" in r["description"] for r in rows)


def test_extract_keeps_unconverted_purchase_at_face_value():
    rows = extract_kotak_transactions(RAW_EXCERPT)
    thai = next(r for r in rows if "THAI BEACH" in r["description"])
    assert thai["category"] == "Hotels"
    assert thai["amount"] == "2,800.00"
    assert thai["is_credit"] is False


def test_extract_includes_emi_principal_and_interest():
    rows = extract_kotak_transactions(RAW_EXCERPT)
    prin = next(r for r in rows if "PRIN FOR RTRADERS" in r["description"])
    intr = next(r for r in rows if "INT-RTRADERS" in r["description"])
    assert prin["amount"] == "527.93"
    assert intr["amount"] == "179.79"


def test_extract_parses_fee_line():
    rows = extract_kotak_transactions(RAW_EXCERPT)
    gst = next(r for r in rows if r["description"] == "GST")
    assert gst["amount"] == "114.39"
    assert gst["category"] == "Fees"


def test_output_feeds_existing_kotak_parser():
    md = kotak_pdf_text_to_md(RAW_EXCERPT)
    parsed = parse_kotak(md)
    assert len(parsed) == 6


def test_output_sum_matches_statement_total_amount_due():
    md = kotak_pdf_text_to_md(RAW_EXCERPT)
    parsed = parse_kotak(md)
    total = sum(r["amount_inr"] for r in parsed)
    # THAI BEACH RESORT (2800.00) + PRIN/INT for FOOD BARN + RTRADERS
    # (181.19+93.57+527.93+179.79=982.48) + GST (114.39) = 3896.87
    assert total == pytest.approx(3896.87)
