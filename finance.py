import click
from parsers import parse_statement
from categorizer import categorize_transactions
from sheets import append_rows, read_all

@click.group()
def cli():
    pass

@cli.command()
@click.option("--file", required=True, help="Path to CC statement .md file")
@click.option("--dry-run", is_flag=True, help="Parse and print without writing to Sheets")
def parse(file, dry_run):
    """Parse a CC statement MD file and append to Transactions sheet."""
    with open(file, "r") as f:
        content = f.read()

    rows = parse_statement(content)
    rows = categorize_transactions(rows)

    # dedup: check existing transactions
    existing = read_all("Transactions")
    existing_keys = {
        (r["date"], r["merchant"], float(r["amount_inr"]))
        for r in existing
        if r.get("amount_inr") not in ("", None)
    }

    new_rows = [
        r for r in rows
        if (r["date"], r["merchant"], float(r["amount_inr"])) not in existing_keys
    ]

    skipped = len(rows) - len(new_rows)
    needs_review = [r for r in new_rows if r.get("_confidence", 100) < 80]

    if dry_run:
        for r in new_rows:
            click.echo(f"{r['date']} | {r['merchant'][:40]:40} | {r['amount']:>10.2f} {r['currency']} | {r['category']}/{r['subcategory']}")
        click.echo(f"\n{len(new_rows)} new rows (dry run — not written)")
        return

    if new_rows:
        sheet_rows = [
            [r["date"], r["card_account"], r["merchant"], r["amount"],
             r["currency"], r["exchange_rate"], r["amount_inr"],
             r["category"], r["subcategory"], r["budget_type"],
             r["payment_method"], r["notes"]]
            for r in new_rows
        ]
        append_rows("Transactions", sheet_rows)

    click.echo(f"✓ {len(new_rows)} rows written, {skipped} duplicates skipped")
    if needs_review:
        click.echo(f"⚠  {len(needs_review)} rows need category review (confidence < 80%):")
        for r in needs_review:
            click.echo(f"   {r['date']} | {r['merchant'][:40]} | {r['amount']} {r['currency']}")

if __name__ == "__main__":
    cli()
