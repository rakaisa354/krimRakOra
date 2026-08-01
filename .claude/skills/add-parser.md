# Skill: add-parser

Use this skill whenever you need to add a new credit card parser to `parsers/`.

## Inputs needed
Before starting, obtain from the user:
1. The card name (e.g. "Axis My Zone")
2. A sample MD statement file (at least 10 rows)
3. Any quirks mentioned (e.g. "has a rewards column", "uses + for debits")

## Steps

### 1. Analyse the MD format
Read the sample file. Identify:
- Header line that identifies the card (used in `detect_card_type`)
- Table header row (columns)
- Date format (DD/MM/YYYY vs YYYY-MM-DD vs MMM DD, YYYY)
- Amount column: suffix for credit? (CR, +, C, refund label?)
- Foreign currency: is it embedded in the description or a separate column?
- EMI rows: do they appear as separate Interest/Principal rows?
- Any junk rows to skip (rewards points, summary rows, blank lines)

### 2. Create `parsers/<cardname>.py`
Follow this template exactly:

```python
"""
Parser for <Card Name> credit card statements.
MD format: <describe table columns>
"""
import re
from datetime import datetime
from fx import convert_to_inr

CARD_ACCOUNT = "<Full Card Name as in Sheets>"

def parse(md_content: str) -> list[dict]:
    rows = []
    in_table = False

    for line in md_content.splitlines():
        line = line.strip()

        # Skip header and separator rows
        if line.startswith("| Date") or line.startswith("|---"):
            in_table = True
            continue
        if not in_table or not line.startswith("|"):
            continue

        cols = [c.strip() for c in line.split("|")[1:-1]]
        if len(cols) < <expected_col_count>:
            continue

        try:
            date_raw = cols[<date_col_idx>]
            date = datetime.strptime(date_raw, "<date_fmt>").strftime("%Y-%m-%d")

            merchant = cols[<merchant_col_idx>].strip()

            # Amount + currency
            amount_raw = cols[<amount_col_idx>].replace(",", "").strip()
            is_credit = amount_raw.endswith("CR")  # adjust suffix per card
            amount = float(amount_raw.rstrip("CR").strip())
            if is_credit:
                amount = -amount  # credits are negative

            currency = "INR"  # change if card has forex col
            exchange_rate = 1.0
            amount_inr = convert_to_inr(amount, currency, date)

            rows.append({
                "date": date,
                "card_account": CARD_ACCOUNT,
                "merchant": merchant,
                "amount": amount,
                "currency": currency,
                "exchange_rate": exchange_rate,
                "amount_inr": amount_inr,
                "category": "",
                "subcategory": "",
                "budget_type": "",
                "payment_method": CARD_ACCOUNT,
                "notes": "",
            })
        except (ValueError, IndexError):
            continue  # skip malformed rows

    return rows
```

### 3. Register in `parsers/__init__.py`
Add import and detection:
```python
from parsers.<cardname> import parse as parse_<cardname>
```
In `detect_card_type()`, add:
```python
if "<Unique header string>" in md_content:
    return "<cardname>"
```
In `parsers` dict inside `parse_statement()`:
```python
"<cardname>": parse_<cardname>,
```

### 4. Write a test in `tests/test_<cardname>.py`
```python
from parsers.<cardname> import parse

SAMPLE_MD = """
# <Card Name> Statement
| Date | Description | Amount |
|---|---|---|
| 01/06/2026 | SWIGGY | 350.00 |
| 02/06/2026 | AMAZON | 1200.00CR |
"""

def test_basic_parse():
    rows = parse(SAMPLE_MD)
    assert len(rows) == 2
    assert rows[0]["merchant"] == "SWIGGY"
    assert rows[0]["amount"] == 350.0
    assert rows[0]["currency"] == "INR"
    assert rows[1]["amount"] == -1200.0  # credit

def test_all_fields_present():
    rows = parse(SAMPLE_MD)
    required = ["date","card_account","merchant","amount","currency",
                "exchange_rate","amount_inr","category","subcategory",
                "budget_type","payment_method","notes"]
    for row in rows:
        for field in required:
            assert field in row, f"Missing field: {field}"
```

### 5. Run code-review skill
After implementation, run the `code-review` skill to verify compliance.

### 6. Test end-to-end
```bash
python finance.py parse --file <statement>.md --dry-run
```
Verify: row count matches statement, credits are negative, dates are YYYY-MM-DD.
