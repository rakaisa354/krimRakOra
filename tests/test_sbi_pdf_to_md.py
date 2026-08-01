import pytest
from pdf_to_md import extract_sbi_transactions, sbi_pdf_text_to_md
from parsers.sbi import parse as parse_sbi

# Excerpt verbatim from pdf_decrypt.extract_text() output on a real decrypted
# SBI Card statement (dump/sbi/2026-04-11_9817463420905150_10042026.pdf).
# One transaction per line, "DD Mon YY DESC AMOUNT [C|D|M]" — except IGST
# lines on EMI instalments, which print with no date of their own (a
# sub-line of the EMI row above in the PDF layout).
RAW_EXCERPT = """
14 Mar 26 FUEL SURCHARGE WAIVER EXCL TAX 28.03 C
10 Apr 26 FP EMI 04/12(EXCL TAX   90.75) 3,342.44 M
10 Apr 26 INTEREST ON EMI 504.17 D
IGST DB @ 18.00% 731.32 D
TRANSACTIONS FOR RAKESH KRISHNAN
14 Mar 26 SHELL INDIA MARKETS PR CHENNAI       IN 2,836.66 D
31 Mar 26 GIRI TRADING AGENCY PR MUMBAI        IN 330.00 D
"""


def test_extract_returns_expected_row_count():
    rows = extract_sbi_transactions(RAW_EXCERPT)
    assert len(rows) == 6


def test_extract_captures_credit_suffix():
    rows = extract_sbi_transactions(RAW_EXCERPT)
    fuel = next(r for r in rows if "FUEL SURCHARGE" in r["description"])
    assert fuel["suffix"] == "C"


def test_extract_captures_emi_suffix():
    rows = extract_sbi_transactions(RAW_EXCERPT)
    emi = next(r for r in rows if "FP EMI" in r["description"])
    assert emi["suffix"] == "M"


def test_extract_attaches_dateless_igst_line_to_prior_date():
    rows = extract_sbi_transactions(RAW_EXCERPT)
    igst = next(r for r in rows if "IGST" in r["description"])
    assert igst["date"] == "10 Apr 26"
    assert igst["amount"] == "731.32"
    assert igst["suffix"] == "D"


def test_extract_ignores_section_header_line():
    rows = extract_sbi_transactions(RAW_EXCERPT)
    assert not any("TRANSACTIONS FOR" in r["description"] for r in rows)


def test_output_feeds_existing_sbi_parser():
    md = sbi_pdf_text_to_md(RAW_EXCERPT)
    parsed = parse_sbi(md)
    assert len(parsed) == 6


def test_output_credit_is_negative():
    md = sbi_pdf_text_to_md(RAW_EXCERPT)
    parsed = parse_sbi(md)
    fuel = next(r for r in parsed if "FUEL SURCHARGE" in r["merchant"])
    assert fuel["amount"] < 0


def test_output_emi_row_tagged():
    md = sbi_pdf_text_to_md(RAW_EXCERPT)
    parsed = parse_sbi(md)
    emi = next(r for r in parsed if "FP EMI" in r["merchant"])
    assert emi["payment_method"] == "emi"


def test_output_igst_row_positive_debit():
    md = sbi_pdf_text_to_md(RAW_EXCERPT)
    parsed = parse_sbi(md)
    igst = next(r for r in parsed if "IGST" in r["merchant"])
    assert igst["amount"] == pytest.approx(731.32)
    assert igst["date"] == "2026-04-10"
