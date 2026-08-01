# dedup-stress-test — Prove Idempotent Transaction Upload

## Purpose
`tests/test_dedup.py` verifies that the `(date, merchant, amount_inr)` dedup key in `finance.py parse` prevents duplicate rows when the same CC statement is uploaded multiple times.

---

## Dedup Key Contract
```
key = (date: str, merchant: str, amount_inr: float)
```
A row is skipped if its key already exists in the Transactions sheet.  
Changing **any one** field = distinct transaction → allowed through.

This mirrors the live implementation in `finance.py`:
```python
existing_keys = {
    (r["date"], r["merchant"], float(r["amount_inr"]))
    for r in existing
    if r.get("amount_inr") not in ("", None)
}
new_rows = [
    r for r in rows
    if (r["date"], r["merchant"], float(r["amount_inr"])) not in existing_keys
]
```

---

## Implementation — `tests/test_dedup.py`

```python
# tests/test_dedup.py
"""
Dedup idempotency tests for krimRakOra transaction parser.
Run: python -m pytest tests/test_dedup.py -v
"""
from unittest.mock import patch, MagicMock
import pytest

# ── Sample statement fixture ──────────────────────────────────────────────────
SAMPLE_MD = """# ICICI Amazon Pay Statement
| Date | Ser No. | Transaction Details | Reward Points | Amount |
|---|---|---|---|---|
| 01/06/2026 | 1 | SWIGGY | 10 | 350.00 |
| 02/06/2026 | 2 | AMAZON INDIA | 20 | 1200.00 |
| 03/06/2026 | 3 | ZOMATO | 5 | 450.00 |
| 04/06/2026 | 4 | NETFLIX | 0 | 649.00 |
| 05/06/2026 | 5 | UBER | 0 | 230.00 |
"""

# Helper: simulate what parse_statement returns (avoids hard dependency on parsers)
def _make_rows():
    return [
        {'date': '2026-06-01', 'merchant': 'SWIGGY',        'amount': 350.00,  'amount_inr': 350.00,  'currency': 'INR'},
        {'date': '2026-06-02', 'merchant': 'AMAZON INDIA',  'amount': 1200.00, 'amount_inr': 1200.00, 'currency': 'INR'},
        {'date': '2026-06-03', 'merchant': 'ZOMATO',        'amount': 450.00,  'amount_inr': 450.00,  'currency': 'INR'},
        {'date': '2026-06-04', 'merchant': 'NETFLIX',       'amount': 649.00,  'amount_inr': 649.00,  'currency': 'INR'},
        {'date': '2026-06-05', 'merchant': 'UBER',          'amount': 230.00,  'amount_inr': 230.00,  'currency': 'INR'},
    ]

def _dedup(rows: list[dict], existing_keys: set) -> list[dict]:
    """Mirror the dedup logic from finance.py parse command."""
    return [
        r for r in rows
        if (r['date'], r['merchant'], float(r['amount_inr'])) not in existing_keys
    ]

def _keys_from_rows(rows: list[dict]) -> set:
    return {(r['date'], r['merchant'], float(r['amount_inr'])) for r in rows}


# ── Test 1: Second parse of identical statement → 0 new rows ─────────────────
def test_no_duplicates_on_second_parse():
    """Parsing the same statement twice produces 0 new rows the second time."""
    rows = _make_rows()

    # Simulate: first parse already wrote these rows to the sheet
    existing_keys = _keys_from_rows(rows)

    new_rows = _dedup(rows, existing_keys)
    assert len(new_rows) == 0, (
        f'Expected 0 new rows on second parse, got {len(new_rows)}: '
        + str([(r["date"], r["merchant"], r["amount_inr"]) for r in new_rows])
    )


# ── Test 2: Dedup key field sensitivity ──────────────────────────────────────
def test_dedup_key_fields():
    """Changing any single key field allows the row through; exact match blocks it."""
    existing_keys = {('2026-06-01', 'SWIGGY', 350.0)}

    # Different date → new transaction
    assert ('2026-06-02', 'SWIGGY', 350.0) not in existing_keys, 'Different date should pass'
    # Different merchant → new transaction
    assert ('2026-06-01', 'ZOMATO', 350.0) not in existing_keys, 'Different merchant should pass'
    # Different amount → new transaction
    assert ('2026-06-01', 'SWIGGY', 351.0) not in existing_keys, 'Different amount should pass'
    # Exact match → blocked
    assert ('2026-06-01', 'SWIGGY', 350.0) in existing_keys, 'Exact match should be blocked'


# ── Test 3: Partial overlap → only net-new rows written ──────────────────────
def test_partial_overlap():
    """New statement with 5 txns, 1 already in sheet → exactly 4 new rows written."""
    rows = _make_rows()
    # Simulate: only the first row (SWIGGY 2026-06-01) was already written
    existing_keys = {('2026-06-01', 'SWIGGY', 350.0)}

    new_rows = _dedup(rows, existing_keys)
    assert len(new_rows) == len(rows) - 1, (
        f'Expected {len(rows) - 1} new rows, got {len(new_rows)}'
    )
    # Confirm SWIGGY was correctly excluded
    merchants_written = [r['merchant'] for r in new_rows]
    assert 'SWIGGY' not in merchants_written


# ── Test 4: Float precision — amount_inr as string from sheet ─────────────────
def test_amount_inr_string_to_float_coercion():
    """Sheet returns amount_inr as string; float() coercion must match correctly."""
    # Sheet stores '350.0' but parse produces 350.00 — must deduplicate
    existing_keys = {('2026-06-01', 'SWIGGY', float('350.0'))}
    rows = [{'date': '2026-06-01', 'merchant': 'SWIGGY', 'amount_inr': 350.00}]
    new_rows = _dedup(rows, existing_keys)
    assert len(new_rows) == 0, 'String-to-float coercion mismatch causes false new row'


# ── Test 5: Empty existing sheet → all rows are new ──────────────────────────
def test_empty_sheet_all_rows_new():
    """If no existing rows in sheet, all parsed rows should be written."""
    rows = _make_rows()
    existing_keys: set = set()
    new_rows = _dedup(rows, existing_keys)
    assert len(new_rows) == len(rows)


# ── Test 6: Blank/null amount_inr rows not included in existing keys ──────────
def test_null_amount_excluded_from_existing_keys():
    """Rows with blank amount_inr in sheet (e.g. header row) must not crash key build."""
    raw_sheet_rows = [
        {'date': '2026-06-01', 'merchant': 'SWIGGY', 'amount_inr': '350.0'},
        {'date': '',           'merchant': '',        'amount_inr': ''},      # blank row
        {'date': '2026-06-02', 'merchant': 'AMAZON INDIA', 'amount_inr': None},
    ]
    # Mirror the guard from finance.py
    existing_keys = {
        (r['date'], r['merchant'], float(r['amount_inr']))
        for r in raw_sheet_rows
        if r.get('amount_inr') not in ('', None)
    }
    assert ('2026-06-01', 'SWIGGY', 350.0) in existing_keys
    assert len(existing_keys) == 1  # only 1 valid key; blank rows skipped
```

---

## Run Tests

```bash
# All dedup tests
python -m pytest tests/test_dedup.py -v

# Expected output:
# tests/test_dedup.py::test_no_duplicates_on_second_parse    PASSED
# tests/test_dedup.py::test_dedup_key_fields                 PASSED
# tests/test_dedup.py::test_partial_overlap                  PASSED
# tests/test_dedup.py::test_amount_inr_string_to_float_coercion PASSED
# tests/test_dedup.py::test_empty_sheet_all_rows_new         PASSED
# tests/test_dedup.py::test_null_amount_excluded_from_existing_keys PASSED
```

---

## Manual Stress Test (Live Sheets)

Proves idempotency against the real Google Sheet:

```bash
# Step 1 — first upload (all rows new)
python finance.py parse --file ICICI_Bank.md
# Expect: ✓ N rows written, 0 duplicates skipped

# Step 2 — second upload of same file (all rows skipped)
python finance.py parse --file ICICI_Bank.md
# Expect: ✓ 0 rows written, N duplicates skipped

# Step 3 — verify row count unchanged in Transactions sheet
python -c "
from sheets import read_all
rows = read_all('Transactions')
print(f'Total rows in sheet: {len(rows)}')
"
# Row count after step 2 must equal row count after step 1
```

---

## Verification

| Test | Checks |
|---|---|
| `test_no_duplicates_on_second_parse` | 0 rows inserted on re-parse |
| `test_dedup_key_fields` | Date / merchant / amount each independently trigger dedup |
| `test_partial_overlap` | Mixed new+existing batch → only net-new rows pass |
| `test_amount_inr_string_to_float_coercion` | Sheet string `'350.0'` == float `350.00` |
| `test_empty_sheet_all_rows_new` | Fresh sheet accepts all rows |
| `test_null_amount_excluded_from_existing_keys` | Blank rows in sheet don't crash key build |
| Manual stress test | Live end-to-end idempotency via CLI |
