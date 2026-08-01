# net_worth.py
import click
from sheets import read_all, append_rows
from datetime import date


@click.command()
@click.option('--salary-balance', prompt='Salary account balance (₹)', type=float)
@click.option('--investments', prompt='Investment value (₹)', type=float)
@click.option('--other-assets', prompt='Other assets (₹)', default=0.0, type=float)
def snapshot(salary_balance, investments, other_assets):
    """Capture monthly net worth snapshot → appended to Net_Worth sheet."""
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
        prev_nw = float(existing[-1].get('net_worth', 0) or 0)
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
