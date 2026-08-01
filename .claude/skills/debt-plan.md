# Skill: debt-plan

Use this skill to generate or update the debt payoff plan using the avalanche + snowball hybrid strategy.

## When to run
- After any change to the `Debts` sheet (new debt, payment made, interest rate change)
- When user asks "when will I be debt-free?" or "how much to pay extra this month?"
- Phase 4 implementation of `debt_planner.py`

## Algorithm

### Avalanche (primary — mathematically optimal)
Sort debts by interest rate DESC. All extra money goes to the highest-rate debt first.

### Snowball override (quick wins)
Any debt with outstanding < ₹20,000 gets flagged as a quick win. User can choose to kill it first for psychological momentum, then resume avalanche.

### Hybrid logic
```
1. Pay minimums on all debts.
2. Identify quick wins (outstanding < ₹20,000).
3. If user opts for quick win: pay off smallest quick-win first with extra cash.
4. Once quick wins cleared: avalanche order strictly by interest rate DESC.
5. Each month: freed minimum from paid-off debt → rolls into next debt's extra payment.
```

## `debt_planner.py` implementation spec

```python
# Read from Debts sheet:
# debt_name | type | bank | initial_amount | total_outstanding
# | interest_rate | min_payment | emi_amount | due_date
# | payoff_priority | avalanche_order

def run_avalanche(debts: list[dict], extra_monthly: float) -> list[dict]:
    """
    Returns month-by-month schedule.
    Each month entry: {month, payments: {debt_name: amount}, balances: {debt_name: balance}}
    """

def quick_wins(debts: list[dict]) -> list[dict]:
    """Return debts with outstanding < 20000, sorted by outstanding ASC."""

def total_interest(schedule: list[dict], debts: list[dict]) -> float:
    """Total interest paid over the schedule vs minimum-only baseline."""

def print_plan(schedule, debts, extra):
    """
    Output format:
    Debt-free by: MONTH YEAR
    Total interest (avalanche): ₹X
    Interest saved vs minimum-only: ₹Y

    Month-by-month:
    Month | <debt1> | <debt2> | ... | Total Paid
    ...

    Quick wins: <debt_name> (₹X) — pay off in month N
    """
```

## CLI integration
Add to `finance.py`:
```python
@cli.command()
@click.option("--extra", default=0, type=float, help="Extra monthly payment in INR")
@click.option("--quick-wins/--no-quick-wins", default=True)
def debt(extra, quick_wins):
    """Show hybrid avalanche+snowball payoff plan."""
```

## Test cases to verify
1. Single debt → payoff month = ceil(outstanding / (min_payment + extra))
2. Two debts, same rate → order by name (stable sort)
3. Payment frees up minimum → verify snowball effect (freed min rolls to next)
4. quick_wins() returns only debts < ₹20,000
5. total_interest() > 0 for any debt with interest_rate > 0

## After implementation
Run `code-review` skill, then `security-review` skill.
Write payoff schedule to `docs/superpowers/plans/debt-plan-YYYY-MM.txt`.
