import re
from datetime import datetime

from income_parser import EMPLOYER_NAMES, _parse_date

FAMILY_NAMES = ["K RADHA GOURI"]

TXN_START = re.compile(r"\n(\d+) (\d{2} \w{3} \d{4}) ")


def _parse_all_lines(raw_text: str) -> list[dict]:
    """Parse every transaction row out of a Kotak savings statement. Each
    row starts with "<N> <DD Mon YYYY> " at a line boundary, followed by a
    free-text description, then a reference code, then "<amount> <balance>".
    Reads the first two money values in a fixed window right after the
    transaction start (not a variable-length block to the next marker or
    end-of-text) — a variable block for the statement's last transaction
    bleeds into footer/next-page text and picks up the wrong numbers, the
    same bug fixed in income_parser.py's extract_kotak_savings_income()."""
    text = "\n" + raw_text
    starts = list(TXN_START.finditer(text))
    rows = []
    opening_match = re.search(r"Opening Balance\D*([\d,]+\.\d{2})", raw_text)
    prev_balance = float(opening_match.group(1).replace(",", "")) if opening_match else None
    for i, m in enumerate(starts):
        desc_end = starts[i + 1].start() if i + 1 < len(starts) else len(text)
        window = text[m.end():min(desc_end, m.end() + 400)]
        amounts = re.findall(r"[\d,]+\.\d{2}", window)
        if len(amounts) < 2:
            continue
        amount_val = float(amounts[0].replace(",", ""))
        balance_val = float(amounts[1].replace(",", ""))
        description = re.split(r"[\d,]+\.\d{2}", window)[0]
        description = re.sub(r"\s+", " ", description).strip()

        signed_amount = amount_val
        if prev_balance is not None:
            signed_amount = round(balance_val - prev_balance, 2)
        prev_balance = balance_val

        rows.append({
            "date": _parse_date(m.group(2)),
            "description": description,
            "amount": signed_amount,   # positive = credit/deposit, negative = debit/withdrawal
            "balance": balance_val,
        })
    return rows


def classify_savings_transactions(raw_text: str) -> dict:
    """Split a Kotak savings statement into buckets by transaction type.
    Returns dict with keys: salary, sip, cred_club, family, spend, loan, unmatched."""
    rows = _parse_all_lines(raw_text)
    buckets = {"salary": [], "sip": [], "cred_club": [], "family": [], "spend": [], "loan": [], "unmatched": []}

    for r in rows:
        d = r["description"]
        if any(name in d for name in EMPLOYER_NAMES) and "NEFT" in d:
            buckets["salary"].append(r)
        elif "NACH-MUT-DR-TP" in d or "NIPPON IND MF" in d:
            buckets["sip"].append(r)
        elif "CRED Club" in d:
            buckets["cred_club"].append(r)
        elif any(name in d for name in FAMILY_NAMES):
            buckets["family"].append(r)
        elif "Ins Debit" in d or "Pyt Loan" in d:
            buckets["loan"].append(r)
        elif "UPI/" in d:
            buckets["spend"].append(r)
        else:
            buckets["unmatched"].append(r)

    return buckets


def extract_merchant(description: str) -> str:
    m = re.match(r"UPI/([^/]+)/", description)
    if m:
        return m.group(1).strip()
    return description[:40].strip()
