import re
from datetime import datetime

# Known employer names that pay salary into the Kotak savings account
# (407010101437), confirmed by the user. "RENGANAYAKI AGENCIES" hasn't
# appeared in a real statement seen so far — kept here per the user's
# report, not yet verified against real extracted text.
EMPLOYER_NAMES = ["KALS BREWERIES", "RENGANAYAKI AGENCIES"]

TXN_START = re.compile(r"\n(\d+) (\d{2} \w{3} \d{4}) ")


def is_kotak_savings_statement(raw_text: str) -> bool:
    return "Savings Account Transactions" in raw_text and "Account Type  Savings" in raw_text


def extract_kotak_savings_income(raw_text: str) -> list[dict]:
    """Pull salary/income NEFT credit lines out of a Kotak savings account
    statement. Each transaction row starts with "<N> <DD Mon YYYY> " at a
    line boundary. For every employer-name occurrence, find the nearest
    preceding date marker, then read the first two money values in a small
    window right after the employer name: the deposit amount, then the
    running balance printed right after it on the same row. (A block that
    ran to the next transaction marker or end-of-text instead of a fixed
    window picked up footer/next-page numbers for the statement's last
    transaction — this fixed window avoids that.)"""
    text = "\n" + raw_text
    rows = []
    for name in EMPLOYER_NAMES:
        idx = 0
        while True:
            idx = text.find(name, idx)
            if idx == -1:
                break
            preceding_starts = list(TXN_START.finditer(text[:idx]))
            if not preceding_starts:
                idx += 1
                continue
            date_str = preceding_starts[-1].group(2)
            amounts = re.findall(r"[\d,]+\.\d{2}", text[idx:idx + 250])
            if len(amounts) < 2:
                idx += 1
                continue
            amount = float(amounts[0].replace(",", ""))
            rows.append({
                "date": _parse_date(date_str),
                "source": name.title(),
                "amount": amount,
                "currency": "INR",
                "exchange_rate": 1.0,
                "amount_inr": amount,
                "type": "salary",
            })
            idx += 1
    return rows


def _parse_date(date_str: str) -> str:
    return datetime.strptime(date_str, "%d %b %Y").strftime("%Y-%m-%d")
