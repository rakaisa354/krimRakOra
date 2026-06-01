"""
Quick-add a single expense to Transactions sheet.
Used by the Telegram agent via GitHub Actions repository_dispatch.

Usage:
  python3 scripts/quick_add.py \
    --date 2026-06-01 \
    --merchant "Zomato" \
    --amount 350 \
    --currency INR \
    --payment_method upi \
    --notes "Dinner"
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import argparse
from datetime import date
from sheets import append_rows, read_all
from fx import convert_to_inr
from categorizer import categorize_transactions


def quick_add(merchant, amount, currency, payment_method, notes, txn_date):
    row = {
        "date": txn_date,
        "card_account": "Cash/UPI",
        "merchant": merchant,
        "amount": float(amount),
        "currency": currency.upper(),
        "exchange_rate": 1.0,
        "amount_inr": float(amount) if currency.upper() == "INR" else convert_to_inr(float(amount), currency.upper(), txn_date),
        "category": "",
        "subcategory": "",
        "budget_type": "",
        "payment_method": payment_method,
        "notes": notes,
    }

    # Auto-categorize via Claude
    row = categorize_transactions([row])[0]

    sheet_row = [
        row["date"], row["card_account"], row["merchant"],
        row["amount"], row["currency"], row["exchange_rate"], row["amount_inr"],
        row["category"], row["subcategory"], row["budget_type"],
        row["payment_method"], row["notes"],
    ]
    append_rows("Transactions", [sheet_row])

    conf = row.get("_confidence", 100)
    review = " ⚠ low confidence — check category" if conf < 80 else ""
    print(f"✓ Added: {row['date']} | {row['merchant']} | {row['amount_inr']:.2f} INR | {row['category']}/{row['subcategory']}{review}")
    return row


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--merchant", required=True)
    parser.add_argument("--amount", required=True, type=float)
    parser.add_argument("--currency", default="INR")
    parser.add_argument("--payment_method", default="upi")
    parser.add_argument("--notes", default="")
    parser.add_argument("--date", default=date.today().isoformat())
    args = parser.parse_args()

    quick_add(args.merchant, args.amount, args.currency, args.payment_method, args.notes, args.date)
