import click
from parsers import parse_statement, detect_card_type, PARSERS
from categorizer import categorize_transactions
from sheets import append_rows, read_all
from net_worth import snapshot as net_worth_cmd
from report import report as report_cmd
from debt_planner import load_debts, run_avalanche, print_plan
from pdf_decrypt import decrypt_pdf, extract_text, DecryptionError
from pdf_to_md import (
    icici_pdf_text_to_md, rbl_pdf_text_to_md, sbi_pdf_text_to_md,
    scapia_pdf_text_to_md, kotak_pdf_text_to_md,
)
from income_parser import is_kotak_savings_statement, extract_kotak_savings_income
from config import CARD_PASSWORDS

PDF_TO_MD = {
    "icici": icici_pdf_text_to_md,
    "rbl": rbl_pdf_text_to_md,
    "sbi": sbi_pdf_text_to_md,
    "scapia": scapia_pdf_text_to_md,
    "kotak": kotak_pdf_text_to_md,
}

@click.group()
def cli():
    pass

@cli.command()
@click.option("--file", required=True, help="Path to encrypted statement PDF")
@click.option("--out", default=None, help="Output path (default: <file>_decrypted.pdf)")
def decrypt(file, out):
    """Decrypt a password-protected statement PDF using CARD_PASSWORDS from .env."""
    if not CARD_PASSWORDS:
        click.echo("✗ CARD_PASSWORDS not set in .env")
        raise SystemExit(1)
    out = out or file.rsplit(".", 1)[0] + "_decrypted.pdf"
    try:
        decrypt_pdf(file, out, CARD_PASSWORDS)
        click.echo(f"✓ Decrypted → {out}")
    except DecryptionError as e:
        click.echo(f"✗ {e}")
        raise SystemExit(1)

def _parse_kotak_savings_income(raw_text, dry_run):
    """Kotak savings account statement: extract salary/income credits only
    and write to the Income sheet, not Transactions — the account also has
    hundreds of unrelated debits (SIPs, UPI transfers, CC bill payments)
    that this deliberately ignores, per the user's 2026-08-10 scope call."""
    rows = extract_kotak_savings_income(raw_text)

    existing = read_all("Income")
    existing_keys = {
        (r["date"], r["source"], float(r["amount"]))
        for r in existing
        if r.get("amount") not in ("", None)
    }
    new_rows = [r for r in rows if (r["date"], r["source"], r["amount"]) not in existing_keys]
    skipped = len(rows) - len(new_rows)

    if dry_run:
        for r in new_rows:
            click.echo(f"{r['date']} | {r['source']} | ₹{r['amount']:.2f}")
        click.echo(f"\n{len(new_rows)} new income row(s) (dry run — not written)")
        return

    if new_rows:
        sheet_rows = [
            [r["date"], r["source"], r["amount"], r["currency"],
             r["exchange_rate"], r["amount_inr"], r["type"]]
            for r in new_rows
        ]
        append_rows("Income", sheet_rows)

    click.echo(f"✓ {len(new_rows)} income rows written, {skipped} duplicates skipped")

@cli.command()
@click.option("--file", default=None, help="Path to CC statement .md file")
@click.option("--pdf", default=None, help="Path to encrypted statement PDF (decrypt + extract + convert, then parse)")
@click.option("--dry-run", is_flag=True, help="Parse and print without writing to Sheets")
def parse(file, pdf, dry_run):
    """Parse a CC statement (.md file or encrypted PDF) and append to Transactions sheet."""
    if not file and not pdf:
        click.echo("✗ Provide --file or --pdf")
        raise SystemExit(1)
    if file and pdf:
        click.echo("✗ Provide only one of --file or --pdf")
        raise SystemExit(1)

    if pdf:
        if not CARD_PASSWORDS:
            click.echo("✗ CARD_PASSWORDS not set in .env")
            raise SystemExit(1)
        decrypted = pdf.rsplit(".", 1)[0] + "_decrypted.pdf"
        try:
            decrypt_pdf(pdf, decrypted, CARD_PASSWORDS)
        except DecryptionError as e:
            click.echo(f"✗ {e}")
            raise SystemExit(1)
        raw_text = extract_text(decrypted)
        if is_kotak_savings_statement(raw_text):
            _parse_kotak_savings_income(raw_text, dry_run)
            return
        try:
            card_type = detect_card_type(raw_text)
        except ValueError as e:
            click.echo(f"✗ {e}")
            raise SystemExit(1)
        content = PDF_TO_MD[card_type](raw_text)
        # card_type is already known from the raw PDF text; the markdown
        # pdf_to_md.py produces is a bare pipe table with no bank-name
        # header line, so re-running detect_card_type on it would fail.
        rows = PARSERS[card_type](content)
    else:
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
        sheet_rows = []
        for r in new_rows:
            notes = r["notes"]
            if r.get("_confidence", 100) < 80:
                notes = (notes or "") + f" [review: confidence {r['_confidence']}%]"
            sheet_rows.append(
                [r["date"], r["card_account"], r["merchant"], r["amount"],
                 r["currency"], r["exchange_rate"], r["amount_inr"],
                 r["category"], r["subcategory"], r["budget_type"],
                 r["payment_method"], notes]
            )
        append_rows("Transactions", sheet_rows)

    click.echo(f"✓ {len(new_rows)} rows written, {skipped} duplicates skipped")
    if needs_review:
        click.echo(f"⚠  {len(needs_review)} rows need category review (confidence < 80%):")
        for r in needs_review:
            click.echo(f"   {r['date']} | {r['merchant'][:40]} | {r['amount']} {r['currency']}")

@cli.command()
@click.option('--extra', default=0.0, type=float, help='Extra monthly payment in ₹')
@click.option('--quick-wins/--no-quick-wins', default=True, help='Pay quick wins (<₹20k) first')
def debt(extra, quick_wins):
    """Hybrid avalanche + snowball debt payoff plan."""
    debts = load_debts()
    if not debts:
        click.echo('✓ No active debts found in Debts sheet.')
        return
    schedule = run_avalanche(debts, extra_monthly=extra, use_quick_wins=quick_wins)
    print_plan(debts, schedule, extra=extra, use_quick_wins=quick_wins)


cli.add_command(net_worth_cmd, name='worth')
cli.add_command(report_cmd, name='report')


if __name__ == "__main__":
    cli()
