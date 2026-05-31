import re
from datetime import datetime

SKIP_PATTERNS = ["Amortization", "IGST-CI", "IGST DB"]

def parse(md: str) -> list[dict]:
    rows = []
    in_table = False
    for line in md.splitlines():
        if "| Date |" in line and "Transaction Details" in line:
            in_table = True
            continue
        if in_table and line.startswith("|---"):
            continue
        if in_table and line.startswith("|"):
            cols = [c.strip() for c in line.strip("|").split("|")]
            if len(cols) < 5:
                continue
            date_str, _, description, _, amount_str = cols[:5]
            if any(p in description for p in SKIP_PATTERNS):
                continue
            is_credit = amount_str.strip().endswith("CR")
            amount_clean = amount_str.replace("CR", "").replace(",", "").strip()
            try:
                amount = float(amount_clean)
            except ValueError:
                continue
            if is_credit:
                amount = -amount
            rows.append({
                "date": _parse_date(date_str.strip()),
                "card_account": "ICICI Amazon Pay",
                "merchant": description.strip(),
                "amount": amount,
                "currency": "INR",
                "exchange_rate": 1.0,
                "amount_inr": amount,
                "category": "",
                "subcategory": "",
                "budget_type": "",
                "payment_method": "credit_card",
                "notes": "",
            })
    return rows

def _parse_date(date_str: str) -> str:
    for fmt in ("%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(date_str, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return date_str
