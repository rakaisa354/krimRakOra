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
CATEGORIES_SEED: list[list[str]] = [
    # NEEDS
    ['Housing',      'Rent',                'need'],
    ['Housing',      'Maintenance',         'need'],
    ['Housing',      'Electricity',         'need'],
    ['Housing',      'Water',               'need'],
    ['Housing',      'Internet',            'need'],
    ['Housing',      'Gas',                 'need'],
    ['Food',         'Groceries',           'need'],
    ['Food',         'Home cooking',        'need'],
    ['Transport',    'Fuel',                'need'],
    ['Transport',    'Metro/Bus',           'need'],
    ['Transport',    'Auto/Cab commute',    'need'],
    ['Health',       'Medicines',           'need'],
    ['Health',       'Doctor',              'need'],
    ['Health',       'Insurance premium',   'need'],
    ['Personal',     'Toiletries',          'need'],
    ['Personal',     'Haircut',             'need'],
    ['Personal',     'Clothing (basic)',    'need'],
    ['Communication','Mobile recharge',     'need'],
    ['Education',    'Course fees',         'need'],
    ['Education',    'Books',               'need'],
    # WANTS
    ['Food',         'Dining out',          'want'],
    ['Food',         'Swiggy/Zomato',       'want'],
    ['Food',         'Coffee shops',        'want'],
    ['Entertainment','OTT subscriptions',   'want'],
    ['Entertainment','Movies',              'want'],
    ['Entertainment','Gaming',              'want'],
    ['Entertainment','Events/Concerts',     'want'],
    ['Shopping',     'Clothing (fashion)',  'want'],
    ['Shopping',     'Electronics',         'want'],
    ['Shopping',     'Gadgets',             'want'],
    ['Shopping',     'Amazon misc',         'want'],
    ['Travel',       'Flights',             'want'],
    ['Travel',       'Hotels',              'want'],
    ['Travel',       'Cabs (non-commute)',  'want'],
    ['Travel',       'Holiday expenses',    'want'],
    ['Personal',     'Gym/Fitness',         'want'],
    ['Personal',     'Gifts',               'want'],
    ['Personal',     'Personal care (spa)', 'want'],
    # DEBT
    ['Debt',         'Credit card EMI',     'debt'],
    ['Debt',         'Credit card payment', 'debt'],
    ['Debt',         'Personal loan EMI',   'debt'],
    ['Debt',         'Home loan EMI',       'debt'],
    ['Debt',         'Car loan EMI',        'debt'],
    ['Debt',         'Interest charges',    'debt'],
    # SAVINGS
    ['Savings',      'Emergency fund',      'save'],
    ['Savings',      'SIP / MF',            'save'],
    ['Savings',      'FD',                  'save'],
    ['Savings',      'Stocks',              'save'],
    ['Savings',      'Gold',                'save'],
    ['Savings',      'Travel fund',         'save'],
    ['Savings',      'Retirement',          'save'],
    # INCOME
    ['Income',       'Salary',              'income'],
    ['Income',       'Freelance',           'income'],
    ['Income',       'Interest',            'income'],
    ['Income',       'Dividend',            'income'],
    ['Income',       'Reimbursement',       'income'],
    ['Income',       'Other',               'income'],
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
    print(f'    [set] Headers: {ws.title} → {", ".join(headers)}')


def seed_categories(ws: gspread.Worksheet) -> None:
    """Append taxonomy rows only if sheet is empty (header only). Idempotent."""
    all_values = ws.get_all_values()
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
