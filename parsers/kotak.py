import re
from datetime import datetime

def parse(md: str) -> list[dict]:
    rows = []
    in_table = False
    for line in md.splitlines():
        if "| Date |" in line and "Description" in line:
            in_table = True
            continue
        if in_table and line.startswith("|---"):
            continue
        if in_table and line.startswith("|"):
            cols = [c.strip() for c in line.strip("|").split("|")]
            if len(cols) < 3:
                continue
            date_str, description, amount_str = cols[0], cols[1], cols[2]
            if not date_str or date_str.startswith("---") or "---" in date_str:
                continue
            try:
                is_credit = "Cr" in amount_str
                amount_inr = float(re.sub(r"[^\d.]", "", amount_str.replace("Cr", "")))
            except ValueError:
                continue
            if is_credit:
                amount_inr = -amount_inr

            rows.append({
                "date": _parse_date(date_str.strip()),
                "card_account": "Kotak Mahindra Bank",
                "merchant": description.strip(),
                "amount": amount_inr,
                "currency": "INR",
                "exchange_rate": 1.0,
                "amount_inr": amount_inr,
                "category": "",
                "subcategory": "",
                "budget_type": "",
                "payment_method": "credit_card",
                "notes": "",
            })
    return rows

def _parse_date(date_str: str) -> str:
    for fmt in ("%d-%b-%Y", "%d %b %Y", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(date_str, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return date_str
