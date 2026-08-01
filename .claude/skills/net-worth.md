# net-worth — Monthly Net Worth Snapshot

## Purpose
Capture a point-in-time net worth snapshot via interactive CLI prompts, read liabilities automatically from the Debts sheet, compute MoM delta, and append one row to `Net_Worth`.

---

## Net_Worth Sheet — Column Schema
| Column | Type | Notes |
|---|---|---|
| `month` | string | `YYYY-MM` format |
| `total_assets` | float | sum of all asset inputs |
| `total_liabilities` | float | auto-read from Debts sheet |
| `net_worth` | float | `total_assets - total_liabilities` |
| `mom_change` | float | `net_worth - prev_row.net_worth` (0 for first row) |

---

## Implementation — `net_worth.py`

Create at project root alongside `finance.py`.

```python
# net_worth.py
import click
from sheets import read_all, append_rows
from datetime import date

@click.command()
@click.option('--salary-balance', prompt='Salary account balance (₹)', type=float)
@click.option('--investments', prompt='Investment value (₹)', type=float)
@click.option('--other-assets', prompt='Other assets (₹)', default=0.0, type=float)
def snapshot(salary_balance, investments, other_assets):
    """Capture monthly net worth snapshot."""
    # Auto-read liabilities from Debts sheet
    debts = read_all('Debts')
    total_liabilities = sum(
        float(d.get('total_outstanding', 0) or 0)
        for d in debts
    )

    total_assets = salary_balance + investments + other_assets
    net_worth = total_assets - total_liabilities

    # MoM change: compare to last row in Net_Worth
    existing = read_all('Net_Worth')
    mom_change = 0.0
    if existing:
        prev = existing[-1]
        prev_nw = float(prev.get('net_worth', 0) or 0)
        mom_change = net_worth - prev_nw

    month = date.today().strftime('%Y-%m')
    append_rows('Net_Worth', [[
        month,
        total_assets,
        total_liabilities,
        net_worth,
        mom_change
    ]])

    print(f'✓ Net worth {month}: ₹{net_worth:,.0f} ({mom_change:+,.0f} MoM)')
    print(f'  Assets: ₹{total_assets:,.0f}  |  Liabilities: ₹{total_liabilities:,.0f}')

if __name__ == '__main__':
    snapshot()
```

---

## CLI Integration — `finance.py`

Add two lines to `finance.py`:

```python
# At top with other imports
from net_worth import snapshot as net_worth_cmd

# After cli group definition, before if __name__ == '__main__'
cli.add_command(net_worth_cmd, name='worth')
```

Final `finance.py` command list:
- `parse` — existing
- `worth` — new

---

## Data Flow

```
CLI prompts
  └─ salary_balance + investments + other_assets → total_assets

Debts sheet (auto)
  └─ SUM(total_outstanding) → total_liabilities

net_worth = total_assets - total_liabilities
mom_change = net_worth - Net_Worth[-1].net_worth

→ append_rows('Net_Worth', [row])
```

---

## Edge Cases

| Scenario | Handling |
|---|---|
| Debts sheet is empty | `sum()` returns 0 — safe |
| `total_outstanding` cell is blank | `or 0` guard on float conversion |
| First ever snapshot | `mom_change = 0` (no previous row) |
| Running twice in same month | Appends a second row — warn user to check manually; no dedup on Net_Worth |

---

## Verification

```bash
# 1. Dry run via manual values
python finance.py worth \
  --salary-balance 150000 \
  --investments 80000 \
  --other-assets 5000

# 2. Interactive prompts
python finance.py worth

# 3. Confirm sheet row
# Open Google Sheets → Net_Worth tab
# Expect: new row with current YYYY-MM, correct totals, MoM delta
```

Expected terminal output:
```
✓ Net worth 2026-06: ₹1,85,000 (+15,000 MoM)
  Assets: ₹2,35,000  |  Liabilities: ₹50,000
```
