# report.py
import click
from datetime import datetime
from collections import defaultdict
from dateutil.relativedelta import relativedelta
from sheets import read_all


def _month_filter(rows: list[dict], month: str, date_col: str = 'date') -> list[dict]:
    """Return rows where date_col starts with YYYY-MM."""
    return [r for r in rows if str(r.get(date_col, '')).startswith(month)]


def _safe_float(val, default=0.0) -> float:
    try:
        return float(val or default)
    except (ValueError, TypeError):
        return default


def _prev_month(month: str) -> str:
    return (datetime.strptime(month, '%Y-%m') - relativedelta(months=1)).strftime('%Y-%m')


def _mom_line(label: str, curr: float, prev: float, prev_month: str) -> str:
    if prev == 0:
        return f"- {label}: ₹{curr:,.0f} _(no {prev_month} data to compare)_"
    delta = curr - prev
    pct = delta / abs(prev) * 100
    arrow = '▲' if delta > 0 else ('▼' if delta < 0 else '─')
    return f"- {label}: ₹{curr:,.0f} {arrow} {pct:+.0f}% vs ₹{prev:,.0f} ({prev_month})"


BUDGET_SPLITS = {'need': 0.40, 'debt': 0.30, 'save': 0.20, 'want': 0.10}
BUDGET_LABELS = {'need': 'Needs', 'debt': 'Debt', 'save': 'Savings', 'want': 'Wants'}


def _budget_actuals(month: str, budget_rows: list[dict], transactions: list[dict], income_total: float) -> list[dict]:
    """Per-budget_type allocated vs actual for one month. Uses Budget sheet
    rows for that month if present, else falls back to the 40/30/20/10
    split of income_total — same fallback report() always used, now shared
    so month-over-month overrun comparisons use identical logic for both
    months instead of two independently-drifting implementations."""
    budget_month = [r for r in budget_rows if str(r.get('month', '')).startswith(month)]

    actual_by_type: dict[str, float] = defaultdict(float)
    for r in transactions:
        bt = r.get('budget_type', 'Uncategorized')
        actual_by_type[bt] += _safe_float(r.get('amount_inr'))

    rows = []
    if budget_month:
        for b in budget_month:
            bt = b.get('budget_type', b.get('category', ''))
            alloc = _safe_float(b.get('allocated_inr'))
            rows.append({'bt': bt, 'label': BUDGET_LABELS.get(bt, bt), 'alloc': alloc, 'actual': actual_by_type.get(bt, 0.0)})
    else:
        for bt, pct in BUDGET_SPLITS.items():
            alloc = income_total * pct
            rows.append({'bt': bt, 'label': BUDGET_LABELS[bt], 'alloc': alloc, 'actual': actual_by_type.get(bt, 0.0)})
    return rows


def _overrun_lines(curr_rows: list[dict], prev_rows: list[dict], month: str, prev_month: str) -> list[str]:
    """Flag any budget_type over 100% of its allocation in BOTH the current
    and prior month — a single over-budget month is normal variance, two in
    a row is a pattern worth a nudge. Deterministic, no LLM call."""
    prev_by_bt = {r['bt']: r for r in prev_rows}
    lines = []
    for r in curr_rows:
        if r['alloc'] <= 0:
            continue
        curr_pct = r['actual'] / r['alloc'] * 100
        if curr_pct <= 100:
            continue
        prev = prev_by_bt.get(r['bt'])
        if not prev or prev['alloc'] <= 0:
            continue
        prev_pct = prev['actual'] / prev['alloc'] * 100
        if prev_pct <= 100:
            continue
        lines.append(
            f"- **{r['label']}** over budget 2 months running: {curr_pct:.0f}% of allocation this "
            f"month ({month}), {prev_pct:.0f}% last month ({prev_month}). Consider lowering the "
            f"{r['label'].lower()} allocation or cutting spend in this bucket."
        )
    return lines


@click.command()
@click.option('--month', required=True, help='Report month in YYYY-MM format, e.g. 2026-05')
@click.option('--dry-run', is_flag=True, default=False, help='Print report; skip Drive upload')
def report(month: str, dry_run: bool):
    """Generate monthly financial report and optionally upload to Google Drive."""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')

    # ── Read sheets ──────────────────────────────────────────────
    transactions = _month_filter(read_all('Transactions'), month)
    income_rows  = _month_filter(read_all('Income'), month)
    budget_rows  = read_all('Budget')
    debts        = read_all('Debts')
    goals        = read_all('Goals')
    net_worth    = read_all('Net_Worth')

    # ── Income vs Spend ──────────────────────────────────────────
    # Sums ALL signed amounts, not just positives — a positive-only filter
    # double-counts reversed charges (a purchase reversed then re-charged at
    # the true net amount) as real spend instead of netting them out. Same
    # bug already fixed in WF4/WF5's n8n Code nodes and query_budget.py on
    # 2026-08-09; this file had never gotten the same fix.
    income_total = sum(_safe_float(r.get('amount_inr')) for r in income_rows)
    spend_total  = sum(_safe_float(r.get('amount_inr')) for r in transactions)
    saved    = income_total - spend_total
    save_pct = (saved / income_total * 100) if income_total else 0

    # ── Month-over-month ─────────────────────────────────────────
    prev_month = _prev_month(month)
    prev_transactions = _month_filter(read_all('Transactions'), prev_month)
    prev_income_rows  = _month_filter(read_all('Income'), prev_month)
    prev_income_total = sum(_safe_float(r.get('amount_inr')) for r in prev_income_rows)
    prev_spend_total  = sum(_safe_float(r.get('amount_inr')) for r in prev_transactions)
    prev_saved        = prev_income_total - prev_spend_total

    # ── Budget breakdown ─────────────────────────────────────────
    curr_budget_rows = _budget_actuals(month, budget_rows, transactions, income_total)
    budget_table_rows = [(r['label'], r['alloc'], r['actual'], r['alloc'] - r['actual']) for r in curr_budget_rows]

    # ── Budget-overrun coaching ──────────────────────────────────
    # Deterministic heuristic (not a second LLM call): flag any budget_type
    # over 100% of its allocation in both this month and the prior one.
    prev_budget_rows = _budget_actuals(prev_month, budget_rows, prev_transactions, prev_income_total)
    overrun_lines = _overrun_lines(curr_budget_rows, prev_budget_rows, month, prev_month)

    # ── Top merchants ────────────────────────────────────────────
    merchant_spend: dict[str, float] = defaultdict(float)
    for r in transactions:
        merchant_spend[r.get('merchant', 'Unknown')] += _safe_float(r.get('amount_inr'))
    top_merchants = sorted(merchant_spend.items(), key=lambda x: x[1], reverse=True)[:5]

    # ── Debt avalanche priority ──────────────────────────────────
    sorted_debts = sorted(
        [d for d in debts if _safe_float(d.get('total_outstanding')) > 0],
        key=lambda d: _safe_float(d.get('interest_rate')),
        reverse=True
    )
    priority_debt = sorted_debts[0] if sorted_debts else {}

    # ── Goals progress ───────────────────────────────────────────
    goals_progress = []
    for g in goals:
        target = _safe_float(g.get('target_inr'))
        so_far = _safe_float(g.get('saved_so_far'))
        pct    = (so_far / target * 100) if target else 0
        goals_progress.append({'name': g.get('goal_name', ''), 'pct': pct, 'saved': so_far, 'target': target})

    # ── Build report strings ─────────────────────────────────────
    budget_lines = ['| Category | Budget | Actual | Variance |', '|---|---|---|---|']
    for label, alloc, actual, variance in budget_table_rows:
        sign = '+' if variance >= 0 else ''
        budget_lines.append(f'| {label} | ₹{alloc:,.0f} | ₹{actual:,.0f} | {sign}₹{variance:,.0f} |')

    goals_lines = []
    for g in goals_progress:
        filled = int(g['pct'] / 10)
        bar = '█' * filled + '░' * (10 - filled)
        goals_lines.append(f"- {g['name']}: {g['pct']:.0f}% [{bar}] ₹{g['saved']:,.0f} / ₹{g['target']:,.0f}")

    merchant_lines = [f"{i+1}. {m}: ₹{a:,.0f}" for i, (m, a) in enumerate(top_merchants)]

    overrun_section = ''
    if overrun_lines:
        overrun_section = "\n**⚠ Budget overrun watch:**\n" + chr(10).join(overrun_lines) + "\n"

    # Net worth this month
    nw_row = next((r for r in reversed(net_worth) if str(r.get('month', '')).startswith(month)), {})
    nw_section = ''
    if nw_row:
        nw_section = (
            f"\n## Net Worth\n"
            f"₹{_safe_float(nw_row.get('net_worth')):,.0f}  "
            f"({_safe_float(nw_row.get('mom_change')):+,.0f} MoM)\n"
        )

    # Debt section
    debt_section = ''
    if priority_debt:
        debt_section = (
            f"## Debt Avalanche\n"
            f"Priority: **{priority_debt.get('debt_name')}** "
            f"@ {priority_debt.get('interest_rate')}%  \n"
            f"Outstanding: ₹{_safe_float(priority_debt.get('total_outstanding')):,.0f}  \n"
            f"Min payment: ₹{_safe_float(priority_debt.get('min_payment')):,.0f}  "
            f"| EMI: ₹{_safe_float(priority_debt.get('emi_amount')):,.0f}  \n"
            f"Payoff target: {priority_debt.get('due_date', 'TBD')}\n\n"
        )

    mom_lines = [
        _mom_line('Income', income_total, prev_income_total, prev_month),
        _mom_line('Spent', spend_total, prev_spend_total, prev_month),
        _mom_line('Saved', saved, prev_saved, prev_month),
    ]

    md_report = f"""# Financial Report — {month}
Generated: {timestamp}

## Income vs Spend
| Metric | Amount |
|---|---|
| Income | ₹{income_total:,.0f} |
| Spent  | ₹{spend_total:,.0f} |
| Saved  | ₹{saved:,.0f} ({save_pct:.0f}% of income) |

## Month-over-Month
{chr(10).join(mom_lines)}

## Budget Breakdown
{chr(10).join(budget_lines)}
{overrun_section}
{debt_section}## Goals
{chr(10).join(goals_lines) if goals_lines else '_No goals configured._'}
{nw_section}
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
    """Upload markdown string to Google Drive as Report_{month}.md (upsert)."""
    import io
    from google.oauth2.service_account import Credentials
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaIoBaseUpload

    SCOPES = ['https://www.googleapis.com/auth/drive.file']
    creds = Credentials.from_service_account_file('credentials.json', scopes=SCOPES)
    service = build('drive', 'v3', credentials=creds)

    filename = f'Report_{month}.md'
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
        service.files().update(fileId=existing_files[0]['id'], media_body=media).execute()
    else:
        service.files().create(
            body={'name': filename, 'mimeType': 'text/markdown'},
            media_body=media
        ).execute()


if __name__ == '__main__':
    report()
