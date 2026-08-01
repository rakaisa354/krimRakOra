"""
Hybrid avalanche + snowball debt payoff planner.
Reads from Debts sheet, computes month-by-month schedule.

Usage:
  python finance.py debt
  python finance.py debt --extra 5000
  python finance.py debt --extra 5000 --no-quick-wins
"""
import math
from datetime import date
from dateutil.relativedelta import relativedelta
from sheets import read_all


def _safe_float(val, default=0.0) -> float:
    try:
        return float(val or default)
    except (ValueError, TypeError):
        return default


def load_debts() -> list[dict]:
    """Load active debts from Sheets, normalise numeric fields."""
    rows = read_all('Debts')
    debts = []
    for r in rows:
        outstanding = _safe_float(r.get('total_outstanding'))
        if outstanding <= 0:
            continue  # skip cleared debts
        debts.append({
            'name':        r.get('debt_name', 'Unknown'),
            'bank':        r.get('bank', ''),
            'outstanding': outstanding,
            'rate':        _safe_float(r.get('interest_rate')),      # annual %
            'min_payment': _safe_float(r.get('min_payment')),
            'emi':         _safe_float(r.get('emi_amount')),
        })
    return debts


def quick_wins(debts: list[dict]) -> list[dict]:
    """Return debts with outstanding < ₹20,000, sorted by outstanding ASC."""
    return sorted([d for d in debts if d['outstanding'] < 20_000], key=lambda d: d['outstanding'])


def run_avalanche(debts: list[dict], extra_monthly: float, use_quick_wins: bool = True) -> list[dict]:
    """
    Hybrid avalanche + snowball simulation.
    Returns list of monthly dicts:
      {month_label, payments: {name: amount}, balances: {name: balance}, interest_paid: {name: amount}}
    """
    if not debts:
        return []

    # Work on mutable copies
    state = [{**d} for d in debts]

    # Ordering: quick wins first (if enabled), then avalanche by rate DESC
    qw = quick_wins(state) if use_quick_wins else []
    qw_names = {d['name'] for d in qw}

    def payoff_order(ds):
        """Quick wins first (by outstanding ASC), then avalanche (by rate DESC)."""
        qw_part  = sorted([d for d in ds if d['name'] in qw_names], key=lambda d: d['outstanding'])
        av_part  = sorted([d for d in ds if d['name'] not in qw_names], key=lambda d: d['rate'], reverse=True)
        return qw_part + av_part

    schedule = []
    today = date.today()
    month_label = today

    MAX_MONTHS = 360  # 30-year safety cap
    for _ in range(MAX_MONTHS):
        active = [d for d in state if d['outstanding'] > 0]
        if not active:
            break

        month_str = month_label.strftime('%Y-%m')
        payments  = {}
        interest_paid = {}
        monthly_interest_total = 0.0

        # Step 1: accrue monthly interest on each debt
        for d in active:
            monthly_rate = d['rate'] / 100 / 12
            interest = round(d['outstanding'] * monthly_rate, 2)
            d['outstanding'] += interest
            interest_paid[d['name']] = interest
            monthly_interest_total += interest

        # Step 2: pay minimums on all
        freed_minimum = 0.0
        for d in active:
            min_pay = max(d['min_payment'], d['emi'])
            actual_pay = min(min_pay, d['outstanding'])
            d['outstanding'] = max(0, round(d['outstanding'] - actual_pay, 2))
            payments[d['name']] = payments.get(d['name'], 0) + actual_pay
            if d['outstanding'] == 0:
                freed_minimum += min_pay  # minimum rolls to next debt

        # Step 3: apply extra + freed minimums to priority debt
        available_extra = extra_monthly + freed_minimum
        ordered = payoff_order([d for d in active if d['outstanding'] > 0])
        for d in ordered:
            if available_extra <= 0:
                break
            pay = min(available_extra, d['outstanding'])
            d['outstanding'] = max(0, round(d['outstanding'] - pay, 2))
            payments[d['name']] = payments.get(d['name'], 0) + pay
            available_extra -= pay
            if d['outstanding'] == 0:
                freed_minimum += max(d['min_payment'], d['emi'])

        balances = {d['name']: round(d['outstanding'], 2) for d in state}
        schedule.append({
            'month':        month_str,
            'payments':     payments,
            'balances':     balances,
            'interest_paid': interest_paid,
        })

        month_label += relativedelta(months=1)

    return schedule


def total_interest_paid(schedule: list[dict]) -> float:
    """Sum all interest accrued across the full schedule."""
    return sum(
        sum(m['interest_paid'].values())
        for m in schedule
    )


def minimum_only_schedule(debts: list[dict]) -> list[dict]:
    """Baseline: pay only minimums, no extra. Used to compute savings."""
    return run_avalanche(debts, extra_monthly=0, use_quick_wins=False)


def print_plan(debts: list[dict], schedule: list[dict], extra: float, use_quick_wins: bool) -> None:
    if not schedule:
        print('✓ No active debts — you are debt-free!')
        return

    last_month = schedule[-1]['month']
    interest   = total_interest_paid(schedule)
    baseline   = total_interest_paid(minimum_only_schedule(debts))
    saved      = baseline - interest

    qw = quick_wins(debts)
    total_outstanding = sum(d['outstanding'] for d in debts)

    print(f'\n{"─"*55}')
    print(f'  Debt Payoff Plan  |  Extra: ₹{extra:,.0f}/month')
    print(f'{"─"*55}')
    print(f'  Active debts    : {len(debts)}')
    print(f'  Total owed      : ₹{total_outstanding:,.0f}')
    print(f'  Debt-free by    : {last_month}')
    print(f'  Total interest  : ₹{interest:,.0f}')
    print(f'  Interest saved  : ₹{saved:,.0f} vs minimum-only')
    if qw and use_quick_wins:
        print(f'\n  Quick wins (< ₹20,000):')
        for d in qw:
            print(f'    ✂  {d["name"]} — ₹{d["outstanding"]:,.0f} @ {d["rate"]}%')
    print(f'{"─"*55}\n')

    # Month-by-month table (show first 24 months then summarise)
    debt_names = [d['name'] for d in debts]
    col_w = max(len(n) for n in debt_names) + 2

    header = f'{"Month":<9}' + ''.join(f'{n:<{col_w}}' for n in debt_names) + f'{"Total":>10}'
    print(header)
    print('─' * len(header))

    shown = 0
    for m in schedule:
        total_pay = sum(m['payments'].values())
        all_zero  = all(m['balances'][n] == 0 for n in debt_names)
        row = f'{m["month"]:<9}'
        for n in debt_names:
            bal = m['balances'].get(n, 0)
            row += f'{"—" if bal == 0 else f"₹{bal:,.0f}":<{col_w}}'
        row += f'₹{total_pay:>8,.0f}'
        print(row)
        shown += 1
        if shown == 24 and len(schedule) > 24:
            remaining = len(schedule) - 24
            print(f'  ... {remaining} more months ...')
            break

    print()
