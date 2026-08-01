import pytest
from pdf_to_md import extract_icici_transactions, icici_pdf_text_to_md
from parsers.icici import parse as parse_icici

# Excerpt lifted verbatim from a real decrypted ICICI statement's extracted
# text (dump/icici/staging/2026-06-03_..._NORM.md) — mixes plain lines,
# ad-hoc pipe tables, and line-wrapped merchant names.
RAW_EXCERPT = """
Date SerNo. Transaction Details Reward Intl.# Amount (in`)
|     |     |     |     |     |     |     | Points | amount |     |
| --- | --- | --- | --- | --- | --- | --- | ------ | ------ | --- |
|     |     |     |     | 03/05/2026 13342230791 | BBPS Payment received |     |     | 0   | 50,790.00 CR |
| --- | --- | --- | --- | ---------------------- | --------------------- | --- | --- | --- | ------------ |
02/05/2026 13343600249 AMAZON PAY INDIA PVT LT BANGALORE IN 0 5,253.00
02/05/2026 13343699136 AMAZON PAY IN E COMMERC BANGALORE 40 804.00
IN
03/05/2026 13350566699 RAZ*Artisante Mumbai     MH IN 11 1,144.95
05/05/2026 13355328919 AMAZON PAY INDIA PVT LT BANGALORE IN 0 157.06
05/05/2026 13355328933 Interest Amount Amortization - 0 70.00
 Apparel/Grocery-40%  Others-57% <1/12>AMAZON PAY INDIA PVT LT
25/05/2026 13475736317 A J SALON SERVICES CHENNAI IN -30 3,000.00 CR
"""


def test_extract_returns_expected_row_count():
    rows = extract_icici_transactions(RAW_EXCERPT)
    assert len(rows) == 7


def test_extract_handles_pipe_table_row():
    rows = extract_icici_transactions(RAW_EXCERPT)
    bbps = next(r for r in rows if "BBPS" in r["description"])
    assert bbps["amount"] == "50,790.00"
    assert bbps["is_credit"] is True


def test_extract_handles_plain_line_row():
    rows = extract_icici_transactions(RAW_EXCERPT)
    amazon = next(r for r in rows if r["ser_no"] == "13343600249")
    assert amazon["amount"] == "5,253.00"
    assert amazon["is_credit"] is False


def test_extract_ignores_trailing_page_furniture():
    # Chart-legend text ("Apparel/Grocery-40% ... <1/12>AMAZON PAY...") sits
    # between the amount and the next real anchor in the raw PDF text. It
    # must not corrupt the amortization row's amount, and the row is dropped
    # downstream anyway by parsers/icici.py's SKIP_PATTERNS.
    rows = extract_icici_transactions(RAW_EXCERPT)
    amortization = next(r for r in rows if "Amortization" in r["description"])
    assert amortization["amount"] == "70.00"


def test_extract_handles_negative_reward_points():
    rows = extract_icici_transactions(RAW_EXCERPT)
    reversal = next(r for r in rows if r["ser_no"] == "13475736317")
    assert reversal["reward_points"] == "-30"
    assert reversal["is_credit"] is True


def test_output_feeds_existing_icici_parser():
    md = icici_pdf_text_to_md(RAW_EXCERPT)
    parsed = parse_icici(md)
    # Amortization row is filtered by parsers/icici.py's SKIP_PATTERNS
    assert len(parsed) == 6
    assert all("Amortization" not in r["merchant"] for r in parsed)


def test_output_marks_credit_negative():
    md = icici_pdf_text_to_md(RAW_EXCERPT)
    parsed = parse_icici(md)
    bbps = next(r for r in parsed if "BBPS" in r["merchant"])
    assert bbps["amount"] < 0
