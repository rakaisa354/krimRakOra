import re
from datetime import datetime

FOREIGN_PATTERN = re.compile(r"\(([A-Z]{3})\s+([\d.]+)\)")

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
            # Skip separator rows or empty rows
            if not date_str or date_str.startswith("---") or "---" in date_str:
                continue
            # Skip if can't parse amount
            try:
                is_credit = "CR" in amount_str
                amount_inr = float(re.sub(r"[^\d.]", "", amount_str.replace("CR", "")))
            except ValueError:
                continue
            if is_credit:
                amount_inr = -amount_inr

            fx_match = FOREIGN_PATTERN.search(description)
            if fx_match and not is_credit:
                currency = fx_match.group(1)
                amount = float(fx_match.group(2))
                exchange_rate = round(abs(amount_inr) / amount, 4) if amount else 1.0
            else:
                currency = "INR"
                amount = amount_inr
                exchange_rate = 1.0

            rows.append({
                "date": _parse_date(date_str.strip()),
                "card_account": "RBL Bank",
                "merchant": description.strip(),
                "amount": amount,
                "currency": currency,
                "exchange_rate": exchange_rate,
                "amount_inr": amount_inr,
                "category": "",
                "subcategory": "",
                "budget_type": "",
                "payment_method": "credit_card",
                "notes": "",
            })
    return rows

def _parse_date(date_str: str) -> str:
    for fmt in ("%d %b %Y", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(date_str, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return date_str
