import re
from datetime import datetime

CREDIT_KEYWORDS = ["Refund", "Payment", "payment", "refund"]

def parse(md: str) -> list[dict]:
    rows = []
    in_table = False
    for line in md.splitlines():
        if "| Date |" in line and "Merchant" in line:
            in_table = True
            continue
        if in_table and line.startswith("|---"):
            continue
        if in_table and line.startswith("|"):
            cols = [c.strip() for c in line.strip("|").split("|")]
            if len(cols) < 3:
                continue
            date_str, merchant, amount_str = cols[0], cols[1], cols[2]
            is_credit = amount_str.startswith("+") or any(k in merchant for k in CREDIT_KEYWORDS)
            amount_clean = re.sub(r"[^\d.]", "", amount_str)
            try:
                amount = float(amount_clean)
            except ValueError:
                continue
            if is_credit:
                amount = -amount
            rows.append({
                "date": _parse_date(date_str.strip()),
                "card_account": "Scapia Federal",
                "merchant": merchant.strip(),
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
    for fmt in ("%d-%m-%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(date_str, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return date_str
