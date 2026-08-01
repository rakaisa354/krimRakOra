# sheets-setup — Idempotent Sheet Tab Initialisation

## Purpose
`scripts/setup_sheets.py` creates all 9 tabs with correct headers and seeds the Categories taxonomy. Safe to run multiple times — no duplicate tabs or data rows created.

---

## Idempotency Contract
1. **Tab**: if tab already exists, skip creation
2. **Headers**: if row 1 already matches, skip writing
3. **Categories seed**: if any rows already exist, skip seeding

---

## Implementation — `scripts/setup_sheets.py`

```python
# scripts/setup_sheets.py
"""
One-shot (idempotent) setup for all 9 krimRakOra Google Sheet tabs.
Run: python3 scripts/setup_sheets.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))  # project root

import gspread
from google.oauth2.service_account import Credentials
from config import GOOGLE_SHEETS_ID

SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive.readonly',
]

# ── Exact header rows per tab ─────────────────────────────────────────────────
HEADERS: dict[str, list[str]] = {
    'Income': [
        'date', 'source', 'amount', 'currency',
        'exchange_rate', 'amount_inr', 'type'
    ],
    'Transactions': [
        'date', 'card_account', 'merchant', 'amount', 'currency',
        'exchange_rate', 'amount_inr', 'category', 'subcategory',
        'budget_type', 'payment_method', 'notes'
    ],
    'Debts': [
        'debt_name', 'type', 'bank', 'initial_amount', 'total_outstanding',
        'interest_rate', 'min_payment', 'emi_amount', 'due_date',
        'payoff_priority', 'avalanche_order'
    ],
    'Budget': [
        'month', 'category', 'budget_type', 'allocated_inr',
        'spent_inr', 'variance', 'pct_used'
    ],
    'Goals': [
        'goal_name', 'type', 'target_inr', 'saved_so_far',
        'target_date', 'monthly_contribution', 'months_remaining'
    ],
    'Net_Worth': [
        'month', 'total_assets', 'total_liabilities', 'net_worth', 'mom_change'
    ],
    'FX_Rates': [
        'date', 'currency_code', 'rate_to_inr'
    ],
    'Categories': [
        'category', 'subcategory', 'budget_type'
    ],
    'Vendor_Map': [
        'vendor_pattern', 'normalized_name', 'category',
        'subcategory', 'confidence', 'last_seen'
    ],
}

# ── Full Categories taxonomy seed data ────────────────────────────────────────
# Format: [category, subcategory, budget_type]
CATEGORIES_SEED: list[list[str]] = [
    # NEEDS
    ['Housing',      'Rent',                'Needs'],
    ['Housing',      'Maintenance',         'Needs'],
    ['Housing',      'Electricity',         'Needs'],
    ['Housing',      'Water',               'Needs'],
    ['Housing',      'Internet',            'Needs'],
    ['Housing',      'Gas',                 'Needs'],
    ['Food',         'Groceries',           'Needs'],
    ['Food',         'Home cooking',        'Needs'],
    ['Transport',    'Fuel',                'Needs'],
    ['Transport',    'Metro/Bus',           'Needs'],
    ['Transport',    'Auto/Cab commute',    'Needs'],
    ['Health',       'Medicines',           'Needs'],
    ['Health',       'Doctor',              'Needs'],
    ['Health',       'Insurance premium',   'Needs'],
    ['Personal',     'Toiletries',          'Needs'],
    ['Personal',     'Haircut',             'Needs'],
    ['Personal',     'Clothing (basic)',    'Needs'],
    ['Communication','Mobile recharge',     'Needs'],
    ['Education',    'Course fees',         'Needs'],
    ['Education',    'Books',               'Needs'],
    # WANTS
    ['Food',         'Dining out',          'Wants'],
    ['Food',         'Swiggy/Zomato',       'Wants'],
    ['Food',         'Coffee shops',        'Wants'],
    ['Entertainment','OTT subscriptions',   'Wants'],
    ['Entertainment','Movies',              'Wants'],
    ['Entertainment','Gaming',              'Wants'],
    ['Entertainment','Events/Concerts',     'Wants'],
    ['Shopping',     'Clothing (fashion)',  'Wants'],
    ['Shopping',     'Electronics',         'Wants'],
    ['Shopping',     'Gadgets',             'Wants'],
    ['Shopping',     'Amazon misc',         'Wants'],
    ['Travel',       'Flights',             'Wants'],
    ['Travel',       'Hotels',              'Wants'],
    ['Travel',       'Cabs (non-commute)',  'Wants'],
    ['Travel',       'Holiday expenses',    'Wants'],
    ['Personal',     'Gym/Fitness',         'Wants'],
    ['Personal',     'Gifts',               'Wants'],
    ['Personal',     'Personal care (spa)', 'Wants'],
    # DEBT
    ['Debt',         'Credit card EMI',     'Debt'],
    ['Debt',         'Credit card payment', 'Debt'],
    ['Debt',         'Personal loan EMI',   'Debt'],
    ['Debt',         'Home loan EMI',       'Debt'],
    ['Debt',         'Car loan EMI',        'Debt'],
    ['Debt',         'Interest charges',    'Debt'],
    # SAVINGS
    ['Savings',      'Emergency fund',      'Savings'],
    ['Savings',      'SIP / MF',            'Savings'],
    ['Savings',      'FD',                  'Savings'],
    ['Savings',      'Stocks',              'Savings'],
    ['Savings',      'Gold',                'Savings'],
    ['Savings',      'Travel fund',         'Savings'],
    ['Savings',      'Retirement',          'Savings'],
    # INCOME (used in Income tab categorisation)
    ['Income',       'Salary',              'Income'],
    ['Income',       'Freelance',           'Income'],
    ['Income',       'Interest',            'Income'],
    ['Income',       'Dividend',            'Income'],
    ['Income',       'Reimbursement',       'Income'],
    ['Income',       'Other',               'Income'],
]


def get_spreadsheet():
    creds = Credentials.from_service_account_file('credentials.json', scopes=SCOPES)
    client = gspread.authorize(creds)
    return client.open_by_key(GOOGLE_SHEETS_ID)


def ensure_tab(spreadsheet, name: str) -> gspread.Worksheet:
    """Return existing worksheet or create a new one. Idempotent."""
    try:
        ws = spreadsheet.worksheet(name)
        print(f'  [skip] Tab already exists: {name}')
        return ws
    except gspread.WorksheetNotFound:
        ws = spreadsheet.add_worksheet(name, rows=1000, cols=20)
        print(f'  [created] Tab: {name}')
        return ws


def ensure_headers(ws: gspread.Worksheet, headers: list[str]) -> None:
    """Write header row only if row 1 is blank or incorrect. Idempotent."""
    existing = ws.row_values(1)
    if existing == headers:
        print(f'    [skip] Headers already set: {ws.title}')
        return
    ws.update('A1', [headers])
    ws.format('A1:Z1', {'textFormat': {'bold': True}})
    print(f'    [set] Headers: {ws.title} → {headers}')


def seed_categories(ws: gspread.Worksheet) -> None:
    """Append taxonomy rows only if sheet is empty (header only). Idempotent."""
    all_values = ws.get_all_values()
    # all_values[0] = header row, rest = data rows
    if len(all_values) > 1:
        print(f'    [skip] Categories already seeded ({len(all_values) - 1} rows)')
        return
    ws.append_rows(CATEGORIES_SEED, value_input_option='RAW')
    print(f'    [seeded] {len(CATEGORIES_SEED)} category rows')


def main():
    print('── krimRakOra Sheet Setup ────────────────────────')
    spreadsheet = get_spreadsheet()
    print(f'Spreadsheet: {spreadsheet.title}  ({GOOGLE_SHEETS_ID})\n')

    for tab_name, headers in HEADERS.items():
        ws = ensure_tab(spreadsheet, tab_name)
        ensure_headers(ws, headers)
        if tab_name == 'Categories':
            seed_categories(ws)

    print('\n✓ All 9 tabs configured.')


if __name__ == '__main__':
    main()
```

---

## Running the Script

```bash
# From project root
python3 scripts/setup_sheets.py

# Second run (should print [skip] for everything)
python3 scripts/setup_sheets.py
```

---

## Tab Summary

| Tab | Columns | Rows pre-seeded |
|---|---|---|
| Income | 7 | 0 |
| Transactions | 12 | 0 |
| Debts | 11 | 0 |
| Budget | 7 | 0 |
| Goals | 7 | 0 |
| Net_Worth | 5 | 0 |
| FX_Rates | 3 | 0 |
| Categories | 3 | 57 (full taxonomy) |
| Vendor_Map | 6 | 0 |

---

## Idempotency Matrix

| Scenario | Tab creation | Header write | Category seed |
|---|---|---|---|
| First run, blank sheet | ✅ Creates | ✅ Writes | ✅ Seeds |
| Re-run, all correct | ⏭ Skip | ⏭ Skip | ⏭ Skip |
| Tab exists, headers wrong | ⏭ Skip (tab) | ✅ Overwrites | depends |
| Categories has data | ⏭ Skip | ⏭ Skip | ⏭ Skip |

---

## Verification

```bash
python3 scripts/setup_sheets.py
# Expect: 9× [created] or [skip], then "✓ All 9 tabs configured."

# Second run — full idempotency check
python3 scripts/setup_sheets.py
# Expect: all [skip] lines, same final message

# Open sheet in browser:
open "https://docs.google.com/spreadsheets/d/$GOOGLE_SHEETS_ID"
# Confirm: 9 tabs, bold header row 1, Categories tab has 57 data rows
```
