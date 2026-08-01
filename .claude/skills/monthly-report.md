# monthly-report — Generate & Upload Monthly Financial Report

## Purpose
`python finance.py report --month YYYY-MM` reads six sheets, computes income/spend/budget/debt/goals metrics, renders a markdown report, prints it to terminal, and uploads it to Google Drive.

---

## Command Signature

```bash
python finance.py report --month 2026-05           # prints + uploads
python finance.py report --month 2026-05 --dry-run # prints only, no upload
```

---

## Implementation — `report.py`

Create at project root.

```python
# report.py
import click
from datetime import datetime
from collections import defaultdict
from sheets import read_all

def _month_filter(rows: list[dict], month: str, date_col: str = 'date') -> list[dict]:
    """Return rows where date_col starts with YYYY-MM."""
    return [r for r in rows if str(r.get(date_col, '')).startswith(month)]

def _safe_float(val, default=0.0) -> float:
    try:
        return float(val or default)
    except (ValueError, TypeError):
        return default

@click.command()
@click.option('--month', required=True, help='Report month in YYYY-MM format, e.g. 2026-05')
@click.option('--dry-run', is_flag=True, default=False, help='Print report; skip Drive upload')
def report(month: str, dry_run: bool):
    """Generate monthly financial report and optionally upload to Google Drive."""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')

    # ── Read sheets ──────────────────────────────────────────────
    transactions = _month_filter(read_all('Transactions'), month)
    income_rows  = _month_filter(read_all('Income'), month)
    budget_rows  = read_all('Budget')         # filter below — has month col
    debts        = read_all('Debts')
    goals        = read_all('Goals')
    net_worth    = read_all('Net_Worth')

    # ── Income vs Spend ──────────────────────────────────────────
    income_total = sum(_safe_float(r.get('amount_inr')) for r in income_rows)
    spend_total  = sum(
        _safe_float(r.get('amount_inr'))
        for r in transactions
        if _safe_float(r.get('amount_inr')) > 0
    )
    saved     = income_total - spend_total
    save_pct  = (saved / income_total * 100) if income_total else 0

    # ── Budget breakdown ─────────────────────────────────────────
    # Budget sheet has month col; filter to current month
    budget_month = [r for r in budget_rows if str(r.get('month', '')).startswith(month)]

    # Actual spend by budget_type from Transactions
    actual_by_type: dict[str, float] = defaultdict(float)
    for r in transactions:
        bt = r.get('budget_type', 'Uncategorized')
        actual_by_type[bt] += _safe_float(r.get('amount_inr'))

    # If no Budget rows for the month, derive allocations from income (40/30/20/10)
    BUDGET_SPLITS = {'Needs': 0.40, 'Debt': 0.30, 'Savings': 0.20, 'Wants': 0.10}
    budget_table_rows = []
    if budget_month:
        for b in budget_month:
            bt       = b.get('budget_type', b.get('category', ''))
            alloc    = _safe_float(b.get('allocated_inr'))
            actual   = actual_by_type.get(bt, 0.0)
            variance = alloc - actual
            budget_table_rows.append((bt, alloc, actual, variance))
    else:
        for bt, pct in BUDGET_SPLITS.items():
            alloc    = income_total * pct
            actual   = actual_by_type.get(bt, 0.0)
            variance = alloc - actual
            budget_table_rows.append((bt, alloc, actual, variance))

    # ── Top merchants ────────────────────────────────────────────
    merchant_spend: dict[str, float] = defaultdict(float)
    for r in transactions:
        merchant_spend[r.get('merchant', 'Unknown')] += _safe_float(r.get('amount_inr'))
    top_merchants = sorted(merchant_spend.items(), key=lambda x: x[1], reverse=True)[:5]

    # ── Debt avalanche priority ──────────────────────────────────
    sorted_debts = sorted(
        debts, key=lambda d: _safe_float(d.get('interest_rate')), reverse=True
    )
    priority_debt = sorted_debts[0] if sorted_debts else {}

    # ── Goals progress ───────────────────────────────────────────
    goals_progress = []
    for g in goals:
        target   = _safe_float(g.get('target_inr'))
        so_far   = _safe_float(g.get('saved_so_far'))
        pct      = (so_far / target * 100) if target else 0
        goals_progress.append({
            'name': g.get('goal_name', ''),
            'pct': pct,
            'saved': so_far,
            'target': target,
        })

    # ── Build budget table string ────────────────────────────────
    budget_lines = ['| Category | Budget | Actual | Variance |', '|---|---|---|---|']
    for bt, alloc, actual, variance in budget_table_rows:
        sign = '+' if variance >= 0 else ''
        budget_lines.append(
            f'| {bt} | ₹{alloc:,.0f} | ₹{actual:,.0f} | {sign}₹{variance:,.0f} |'
        )

    # ── Build goals string ───────────────────────────────────────
    goals_lines = []
    for g in goals_progress:
        bar = '█' * int(g['pct'] / 10) + '░' * (10 - int(g['pct'] / 10))
        goals_lines.append(
            f"- {g['name']}: {g['pct']:.0f}% [{bar}] ₹{g['saved']:,.0f} / ₹{g['target']:,.0f}"
        )

    # ── Build merchants string ───────────────────────────────────
    merchant_lines = [
        f"{i+1}. {m}: ₹{a:,.0f}" for i, (m, a) in enumerate(top_merchants)
    ]

    # ── Net worth this month ─────────────────────────────────────
    nw_row = next((r for r in reversed(net_worth) if str(r.get('month', '')).startswith(month)), {})
    nw_line = ''
    if nw_row:
        nw_line = (
            f"\n## Net Worth\n"
            f"₹{_safe_float(nw_row.get('net_worth')):,.0f}  "
            f"({_safe_float(nw_row.get('mom_change')):+,.0f} MoM)\n"
        )

    # ── Render markdown ──────────────────────────────────────────
    debt_section = ''
    if priority_debt:
        debt_section = (
            f"## Debt Avalanche\n"
            f"Priority: **{priority_debt.get('debt_name')}** "
            f"@ {priority_debt.get('interest_rate')}%  \n"
            f"Outstanding: ₹{_safe_float(priority_debt.get('total_outstanding')):,.0f}  \n"
            f"Min payment: ₹{_safe_float(priority_debt.get('min_payment')):,.0f}  "
            f"| EMI: ₹{_safe_float(priority_debt.get('emi_amount')):,.0f}  \n"
            f"Payoff target: {priority_debt.get('due_date', 'TBD')}\n"
        )

    md_report = f"""# Financial Report — {month}
Generated: {timestamp}

## Income vs Spend
| Metric | Amount |
|---|---|
| Income | ₹{income_total:,.0f} |
| Spent  | ₹{spend_total:,.0f} |
| Saved  | ₹{saved:,.0f} ({save_pct:.0f}% of income) |

## Budget Breakdown
{chr(10).join(budget_lines)}

{debt_section}
## Goals
{chr(10).join(goals_lines) if goals_lines else '_No goals configured._'}
{nw_line}
## Top 5 Merchants
{chr(10).join(merchant_lines) if merchant_lines else '_No transactions this month._'}
"""

    click.echo(md_report)

    if dry_run:
        click.echo('(dry-run — report not uploaded to Drive)')
        return

    _upload_to_drive(md_report, month)
    click.echo(f'✓ Report uploaded to Drive: Report_{month}.md')


def _upload_to_drive(content: str, month: str) -> None:
    """Upload markdown string to Google Drive root as Report_{month}.md."""
    import io
    from google.oauth2.service_account import Credentials
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaIoBaseUpload

    SCOPES = ['https://www.googleapis.com/auth/drive.file']
    creds = Credentials.from_service_account_file('credentials.json', scopes=SCOPES)
    service = build('drive', 'v3', credentials=creds)

    filename = f'Report_{month}.md'

    # Check if file already exists → update instead of creating duplicate
    results = service.files().list(
        q=f"name='{filename}' and trashed=false",
        fields='files(id, name)'
    ).execute()
    existing_files = results.get('files', [])

    media = MediaIoBaseUpload(
        io.BytesIO(content.encode('utf-8')),
        mimetype='text/markdown',
        resumable=False
    )

    if existing_files:
        file_id = existing_files[0]['id']
        service.files().update(fileId=file_id, media_body=media).execute()
    else:
        file_metadata = {'name': filename, 'mimeType': 'text/markdown'}
        service.files().create(body=file_metadata, media_body=media).execute()
```

---

## CLI Integration — `finance.py`

```python
# At top with other imports
from report import report as report_cmd

# After cli group definition
cli.add_command(report_cmd, name='report')
```

---

## Dependencies

Add to `requirements.txt`:
```
google-api-python-client>=2.0
```

Install: `pip install google-api-python-client`

The `credentials.json` service account must have **Google Drive API** enabled and the `drive.file` scope is sufficient for creating/updating files owned by the service account. To share with a human account, add that email as an editor on the Drive folder.

---

## Sheet Columns Read

| Sheet | Columns used |
|---|---|
| `Transactions` | `date`, `amount_inr`, `budget_type`, `merchant` |
| `Income` | `date`, `amount_inr` |
| `Budget` | `month`, `budget_type`, `allocated_inr` |
| `Debts` | `debt_name`, `interest_rate`, `total_outstanding`, `min_payment`, `emi_amount`, `due_date` |
| `Goals` | `goal_name`, `target_inr`, `saved_so_far` |
| `Net_Worth` | `month`, `net_worth`, `mom_change` |

---

## Verification

```bash
# 1. Dry-run (no Drive upload)
python finance.py report --month 2026-05 --dry-run

# 2. Live upload
python finance.py report --month 2026-05

# 3. Confirm file on Drive
# drive.google.com → search "Report_2026-05.md"
# Or via API:
python -c "
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials
creds = Credentials.from_service_account_file('credentials.json', scopes=['https://www.googleapis.com/auth/drive.readonly'])
svc = build('drive', 'v3', credentials=creds)
print(svc.files().list(q=\"name='Report_2026-05.md'\", fields='files(id,name)').execute())
"
```
