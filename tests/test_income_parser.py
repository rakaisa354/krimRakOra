from income_parser import extract_kotak_savings_income, is_kotak_savings_statement

# Excerpt verbatim from pdf_decrypt.extract_text() output on a real decrypted
# Kotak savings account statement (dump/kotak/*_40XXXXXXX437*, July 2026
# cycle) — the account salary lands in, distinct from the Kotak Cashback+
# credit card statement the existing kotak parser handles.
RAW_EXCERPT = """52 30 Jul 2026 UPI/VASUDEVAN R/HDFC/657725007490/Paid
via CRE
UPI-621102673224 1,000.00 29,707.72
53 31 Jul 2026 NEFT HDFCH01159246906 KALS BREWERIES
PVT LTD HDFC
NEFTINW-1667589570 1,83,842.00 2,13,549.72
K RAKESH
Account No. 407010101437
Account Statement 01 Jul 2026 - 31 Jul 2026
Savings Account Transactions
"""

STATEMENT_HEADER = """Account Statement01 Jul 2026 - 31 Jul 2026
Account Type  Savings
Savings Account Transactions
# Date Description Chq/Ref. No. Withdrawal (Dr.) Deposit (Cr.) Balance
"""


def test_is_kotak_savings_statement_true_for_savings():
    assert is_kotak_savings_statement(STATEMENT_HEADER)


def test_is_kotak_savings_statement_false_for_cc():
    cc_text = "Transactions Details from 06-May-2026 to 05-Jun-2026\nPurchases made in this cycle - Primary Card X8502"
    assert not is_kotak_savings_statement(cc_text)


def test_extracts_salary_credit_not_running_balance():
    rows = extract_kotak_savings_income(RAW_EXCERPT)
    assert len(rows) == 1
    r = rows[0]
    assert r["date"] == "2026-07-31"
    assert r["source"] == "Kals Breweries"
    assert r["amount"] == 183842.0
    assert r["type"] == "salary"


def test_ignores_unrelated_upi_credit():
    rows = extract_kotak_savings_income(RAW_EXCERPT)
    sources = [r["source"] for r in rows]
    assert "Vasudevan R" not in sources


def test_no_match_returns_empty():
    assert extract_kotak_savings_income("no employer names here") == []
