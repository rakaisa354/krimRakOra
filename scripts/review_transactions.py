import re
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import click
from sheets import read_all, update_row
from scripts.setup_sheets import HEADERS

REVIEW_TAG = re.compile(r"\s*\[review:[^\]]*\]")


@click.command()
def review():
    """Walk through Transactions rows flagged '[review: ...]' and let the user fix category/subcategory/budget_type."""
    rows = read_all("Transactions")
    flagged = [(i, r) for i, r in enumerate(rows, start=1) if "[review:" in (r.get("notes") or "")]

    if not flagged:
        click.echo("✓ No rows pending review")
        return

    click.echo(f"{len(flagged)} row(s) pending review\n")
    for row_number, r in flagged:
        click.echo(f"{r['date']} | {r['merchant']} | ₹{r['amount_inr']}")
        click.echo(f"  current: {r['category']}/{r['subcategory']}/{r['budget_type']}")
        click.echo(f"  flag: {r.get('notes') or ''}")
        if not click.confirm("  fix this row?", default=True):
            continue

        category = click.prompt("  category", default=r["category"])
        subcategory = click.prompt("  subcategory", default=r["subcategory"])
        budget_type = click.prompt("  budget_type", default=r["budget_type"])
        notes = REVIEW_TAG.sub("", r.get("notes") or "").strip()

        values = [r[h] for h in HEADERS["Transactions"]]
        idx = HEADERS["Transactions"]
        values[idx.index("category")] = category
        values[idx.index("subcategory")] = subcategory
        values[idx.index("budget_type")] = budget_type
        values[idx.index("notes")] = notes

        update_row("Transactions", row_number, values)
        click.echo("  ✓ updated\n")


if __name__ == "__main__":
    review()
