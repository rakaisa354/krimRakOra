"""
Query spending summary for the Telegram agent.
Returns a short text summary of this month's spend by category.

Usage:
  python3 scripts/query_budget.py
  python3 scripts/query_budget.py --month 2026-05
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import argparse
from datetime import date
from collections import defaultdict
from sheets import read_all


def summarize(month: str) -> str:
    transactions = read_all("Transactions")

    month_txns = [
        t for t in transactions
        if str(t.get("date", "")).startswith(month)
        and float(t.get("amount_inr", 0)) > 0  # exclude credits
    ]

    if not month_txns:
        return f"No transactions found for {month}."

    by_budget_type = defaultdict(float)
    by_category = defaultdict(float)
    total = 0.0

    for t in month_txns:
        amt = float(t.get("amount_inr", 0))
        bt = t.get("budget_type", "unknown") or "unknown"
        cat = t.get("category", "unknown") or "unknown"
        by_budget_type[bt] += amt
        by_category[cat] += amt
        total += amt

    lines = [f"📊 *{month} Spending Summary*", f"Total: ₹{total:,.0f}", ""]

    # Budget type breakdown
    budget_labels = {"need": "🏠 Needs", "want": "🎯 Wants", "debt": "💳 Debt", "save": "💰 Savings"}
    for bt in ["need", "want", "debt", "save"]:
        if bt in by_budget_type:
            pct = by_budget_type[bt] / total * 100
            label = budget_labels.get(bt, bt)
            lines.append(f"{label}: ₹{by_budget_type[bt]:,.0f} ({pct:.0f}%)")

    lines.append("")
    lines.append("*Top categories:*")
    top_cats = sorted(by_category.items(), key=lambda x: x[1], reverse=True)[:5]
    for cat, amt in top_cats:
        lines.append(f"  {cat}: ₹{amt:,.0f}")

    lines.append(f"\n_{len(month_txns)} transactions_")
    return "\n".join(lines)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--month", default=date.today().strftime("%Y-%m"))
    args = parser.parse_args()
    print(summarize(args.month))
