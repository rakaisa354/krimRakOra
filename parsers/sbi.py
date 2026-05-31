import re
from datetime import datetime

def parse(md: str) -> list[dict]:
    """Parse SBI Card statement from markdown format."""
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
            if len(cols) < 3:
                continue
            date_str, description, amount_str = cols[0], cols[1], cols[2]

            # Extract suffix (C/D/M) and clean amount
            suffix = amount_str.strip()[-1] if amount_str.strip() else ""
            amount_clean = re.sub(r"[^\d.]", "", amount_str)

            try:
                amount = float(amount_clean)
            except ValueError:
                continue

            # Apply sign based on suffix: C=Credit (negative), D=Debit (positive), M=EMI (positive)
            if suffix == "C":
                amount = -amount

            # Determine payment method
            payment_method = "emi" if suffix == "M" else "credit_card"

            rows.append({
                "date": _parse_date(date_str.strip()),
                "card_account": "SBI Card",
                "merchant": description.strip().lstrip("#"),
                "amount": amount,
                "currency": "INR",
                "exchange_rate": 1.0,
                "amount_inr": amount,
                "category": "",
                "subcategory": "",
                "budget_type": "",
                "payment_method": payment_method,
                "notes": "",
            })

    return rows

def _parse_date(date_str: str) -> str:
    """Parse date from 'dd Mon yy' format (e.g., '26 Apr 26')."""
    for fmt in ("%d %b %y", "%d %b %Y"):
        try:
            return datetime.strptime(date_str, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return date_str
