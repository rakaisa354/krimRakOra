"""Module 2/3: decrypted PDF text -> transaction markdown table.

Bridges pdf_decrypt.extract_text() (raw, layout-order PDF text — no clean
tables) to the pipe-table markdown that parsers/*.py already expect
(see ICICI_Bank.md / RBL_Bank.md / tests/test_*.py for the target shapes).
Pure regex, no third-party extraction API. One extractor per issuer,
built and verified against a real decrypted statement before moving on.

Done: icici, rbl. Pending: sbi, scapia (axis/kotak/emirates-nbd have no
downstream parser yet — out of scope until one exists).
"""
import re

# Matches a transaction record start: "DD/MM/YYYY <9-13 digit serial no>"
_ANCHOR = re.compile(r"(\d{2}/\d{2}/\d{4})\s+(\d{9,13})\s+")

# "<reward points> <amount> [CR]" — the reward/amount pair that closes a
# transaction record. Reward points may be negative (reversal rows). Not
# anchored to end-of-string: page furniture (chart legends, footnotes)
# sometimes bleeds in after the amount, so we take the LAST match in the
# blob and discard anything past it rather than requiring a clean end.
_TAIL = re.compile(r"(-?\d+)\s+([\d,]+\.\d{2})\s*(CR)?")


def _clean(raw_text: str) -> str:
    """Strip markdown pipe-table decoration and collapse whitespace.

    Statement text (whether from markitdown or pypdf) mixes plain lines
    with ad-hoc pipe tables and `|---|` separators for the same logical
    transaction list. Flattening to plain whitespace-joined text lets one
    regex pass handle both.
    """
    lines = []
    for line in raw_text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if re.fullmatch(r"[\s|:-]+", stripped):
            continue
        lines.append(stripped.strip("|").replace("|", " "))
    return " ".join(lines)


def extract_icici_transactions(raw_text: str) -> list[dict]:
    """Parse raw ICICI statement text into transaction dicts.

    Returns dicts with keys: date, ser_no, description, reward_points,
    amount, is_credit. Rows that don't resolve to a trailing amount are
    dropped (section headers / footnotes caught between two anchors).
    """
    text = _clean(raw_text)
    anchors = list(_ANCHOR.finditer(text))
    rows = []
    for i, m in enumerate(anchors):
        date_str, ser_no = m.group(1), m.group(2)
        start = m.end()
        end = anchors[i + 1].start() if i + 1 < len(anchors) else len(text)
        body = text[start:end].strip()

        tail_matches = list(_TAIL.finditer(body))
        if not tail_matches:
            continue
        tail = tail_matches[-1]
        reward_points, amount_str, cr = tail.groups()
        description = body[: tail.start()].strip()
        if not description:
            continue

        rows.append({
            "date": date_str,
            "ser_no": ser_no,
            "description": description,
            "reward_points": reward_points,
            "amount": amount_str,
            "is_credit": bool(cr),
        })
    return rows


def icici_transactions_to_md(rows: list[dict]) -> str:
    """Render extracted rows as the pipe-table parsers/icici.py expects."""
    lines = [
        "| Date | Ser No. | Transaction Details | Reward Points | Amount (₹) |",
        "|---|---|---|---|---|",
    ]
    for r in rows:
        amount = r["amount"] + (" CR" if r["is_credit"] else "")
        lines.append(
            f"| {r['date']} | {r['ser_no']} | {r['description']} | "
            f"{r['reward_points']} | {amount} |"
        )
    return "\n".join(lines)


def icici_pdf_text_to_md(raw_text: str) -> str:
    """One-shot: raw extracted PDF text -> markdown parsers/icici.py can parse."""
    return icici_transactions_to_md(extract_icici_transactions(raw_text))


# --------------------------------------------------------------------------
# RBL Bank
# --------------------------------------------------------------------------
# Unlike ICICI, each RBL transaction prints on a single line — no wrapping,
# no interleaved chart legends. One line-anchored regex is enough.

_RBL_LINE = re.compile(
    r"^(\d{1,2} [A-Za-z]{3} \d{4})\s+(.+?)\s+([\d,]+\.\d{2})\s*$"
)

# RBL's raw text drops the "CR" suffix its own statement PDF shows visually
# for money coming back to the card — payments, cashback, and purchases
# transferred off to an EMI schedule (verified against summary math: the
# "Transferred to EMI" total matches the sum of these lines' amounts in a
# real statement). Detected by keyword instead.
RBL_CREDIT_KEYWORDS = ["PAYMENT", "CASHBACK", "TRANSFERRED TO EMI", "REFUND", "REVERSAL"]

# Raw text renders "CCY( AMT )" attached to the preceding column with no
# space before "(" and stray spaces inside; normalize to "(CCY AMT)" so
# parsers/rbl.py's FOREIGN_PATTERN (\(([A-Z]{3})\s+([\d.]+)\)) matches.
_RBL_FX = re.compile(r"\(\s*([A-Z]{3})\s+([\d,.]+)\s*\)")


def extract_rbl_transactions(raw_text: str) -> list[dict]:
    """Parse raw RBL statement text into transaction dicts.

    Returns dicts with keys: date, description, amount, is_credit.
    """
    rows = []
    for line in raw_text.splitlines():
        m = _RBL_LINE.match(line.strip())
        if not m:
            continue
        date_str, description, amount_str = m.groups()
        description = _RBL_FX.sub(r"(\1 \2)", description)
        description = re.sub(r"\s+", " ", description).strip()
        is_credit = any(k in description.upper() for k in RBL_CREDIT_KEYWORDS)
        rows.append({
            "date": date_str,
            "description": description,
            "amount": amount_str,
            "is_credit": is_credit,
        })
    return rows


def rbl_transactions_to_md(rows: list[dict]) -> str:
    """Render extracted rows as the pipe-table parsers/rbl.py expects."""
    lines = [
        "| Date | Description | Amount (₹) |",
        "|---|---|---|",
    ]
    for r in rows:
        amount = r["amount"] + (" CR" if r["is_credit"] else "")
        lines.append(f"| {r['date']} | {r['description']} | {amount} |")
    return "\n".join(lines)


def rbl_pdf_text_to_md(raw_text: str) -> str:
    """One-shot: raw extracted PDF text -> markdown parsers/rbl.py can parse."""
    return rbl_transactions_to_md(extract_rbl_transactions(raw_text))


# --------------------------------------------------------------------------
# SBI Card
# --------------------------------------------------------------------------
# One transaction per line, format "DD Mon YY DESCRIPTION AMOUNT [C|D|M]"
# (C=credit, D=debit, M=EMI instalment, no suffix = plain debit).

_SBI_LINE = re.compile(
    r"^(\d{1,2} [A-Za-z]{3} \d{2})\s+(.+?)\s+([\d,]+\.\d{2})\s*([CDM])?\s*$"
)

# IGST rows on EMI instalments print without their own date in the raw
# text (they're a sub-line of the EMI row above in the PDF layout) — the
# only dateless line shape seen in a real statement. Narrowly matched
# (must start with "IGST") rather than a generic dateless fallback, since
# the statement's footer/T&C sections are full of unrelated lines that
# also happen to end in a decimal number.
_SBI_IGST_LINE = re.compile(r"^(IGST.+?)\s+([\d,]+\.\d{2})\s*([CDM])?\s*$")


def extract_sbi_transactions(raw_text: str) -> list[dict]:
    """Parse raw SBI Card statement text into transaction dicts.

    Returns dicts with keys: date, description, amount, suffix (one of
    "C", "D", "M", or "" for a plain debit with no printed suffix).
    """
    rows = []
    last_date = None
    for line in raw_text.splitlines():
        line = line.strip()
        m = _SBI_LINE.match(line)
        if m:
            date_str, description, amount_str, suffix = m.groups()
            last_date = date_str
            rows.append({
                "date": date_str,
                "description": description.strip(),
                "amount": amount_str,
                "suffix": suffix or "",
            })
            continue
        if last_date:
            m = _SBI_IGST_LINE.match(line)
            if m:
                description, amount_str, suffix = m.groups()
                rows.append({
                    "date": last_date,
                    "description": description.strip(),
                    "amount": amount_str,
                    "suffix": suffix or "",
                })
    return rows


def sbi_transactions_to_md(rows: list[dict]) -> str:
    """Render extracted rows as the pipe-table parsers/sbi.py expects."""
    lines = [
        "| Date | Transaction Details | Amount (₹) |",
        "|---|---|---|",
    ]
    for r in rows:
        amount = r["amount"] + (f" {r['suffix']}" if r["suffix"] else "")
        lines.append(f"| {r['date']} | {r['description']} | {amount} |")
    return "\n".join(lines)


def sbi_pdf_text_to_md(raw_text: str) -> str:
    """One-shot: raw extracted PDF text -> markdown parsers/sbi.py can parse."""
    return sbi_transactions_to_md(extract_sbi_transactions(raw_text))


# --------------------------------------------------------------------------
# Scapia Federal
# --------------------------------------------------------------------------
# Raw text has no spaces between words within a single PDF text run (e.g.
# "EmelemGourmetLlp"), long merchant names wrap onto their own line before
# the amount, and a repeated page-header block (name / masked card numbers
# / billing cycle) bleeds into the transaction list at each page break —
# same shape of noise as ICICI's chart-legend problem, so the same
# anchor-and-take-last-match strategy handles it.
#
# "YourEMItransactions" rows are excluded on purpose: they're the monthly
# instalment breakdown of purchases already converted to EMI (and already
# counted as spend in the month they happened), not new transactions —
# same reasoning as icici.py's own SKIP_PATTERNS for Amortization rows.

_SCAPIA_ANCHOR = re.compile(r"(\d{2}-\d{2}-\d{4})·\d{2}:\d{2}\s*")
_SCAPIA_AMOUNT = re.compile(r"([+-]?)₹([\d,]+\.\d{2})")


def extract_scapia_transactions(raw_text: str) -> list[dict]:
    """Parse raw Scapia statement text into transaction dicts.

    Returns dicts with keys: date, merchant, amount (no ₹, "+" kept when
    present). Only the "YourTransactions" section is parsed — see module
    note above on why "YourEMItransactions" is excluded.
    """
    start = raw_text.find("YourTransactions")
    if start == -1:
        start = 0
    end = raw_text.find("YourEMItransactions")
    if end == -1:
        end = len(raw_text)
    section = raw_text[start:end]

    anchors = list(_SCAPIA_ANCHOR.finditer(section))
    rows = []
    for i, m in enumerate(anchors):
        date_str = m.group(1)
        body_start = m.end()
        body_end = anchors[i + 1].start() if i + 1 < len(anchors) else len(section)
        body = section[body_start:body_end]

        amt = _SCAPIA_AMOUNT.search(body)
        if not amt:
            continue
        sign, amount_str = amt.groups()
        merchant = body[: amt.start()].strip()
        if not merchant:
            continue

        rows.append({
            "date": date_str,
            "merchant": merchant,
            "amount": (sign if sign == "+" else "") + amount_str,
        })
    return rows


def scapia_transactions_to_md(rows: list[dict]) -> str:
    """Render extracted rows as the pipe-table parsers/scapia.py expects."""
    lines = [
        "| Date | Merchant | Amount (₹) | Coins |",
        "|---|---|---|---|",
    ]
    for r in rows:
        lines.append(f"| {r['date']} | {r['merchant']} | {r['amount']} | |")
    return "\n".join(lines)


def scapia_pdf_text_to_md(raw_text: str) -> str:
    """One-shot: raw extracted PDF text -> markdown parsers/scapia.py can parse."""
    return scapia_transactions_to_md(extract_scapia_transactions(raw_text))


# --------------------------------------------------------------------------
# Kotak Mahindra Bank
# --------------------------------------------------------------------------
# One transaction per line, no wrapping. Three sections matter: "Purchases
# made in this cycle" (each line ends "<description> <3-digit code>
# [(Convert To EMI)] <Spends Category> <Amount>"), "EMI & Loans", and
# "Other fees and charges" (plain "<date> <description> <amount>").
#
# Verified against a real statement (dump/kotak/2026-06-06_..._decrypted.pdf):
# every purchase tagged "(Convert To EMI)" is immediately reversed in the
# SAME statement by a matching "EMI CONV <merchant>(NNN) <same amount> Cr"
# line, and only its "EMI PRIN FOR ..." + "EMI INT-..." sub-lines are new
# money for this cycle — their sum (1,866.33) exactly matches the
# statement's own "Total Purchases" total, and PRIN+INT+GST (1,980.72)
# exactly matches "Total Amount Due". So a "(Convert To EMI)" purchase line
# is EXCLUDED (it nets to zero against its own reversal) and the matching
# PRIN/INT lines are INCLUDED instead. A purchase with no "(Convert To
# EMI)" tag has no matching reversal and is counted at face value.

_KOTAK_PURCHASE_LINE = re.compile(
    r"^(\d{2}-[A-Za-z]{3}-\d{4})\s+(.+?)\s+\d+\s*(\(Convert To EMI\)\s*)?"
    r"([A-Za-z][A-Za-z &]*?)\s+([\d,]+\.\d{2})\s*(Cr)?$"
)
_KOTAK_EMI_CONV_LINE = re.compile(r"^\d{2}-[A-Za-z]{3}-\d{4}\s+EMI CONV\b")
_KOTAK_EMI_INSTALMENT_LINE = re.compile(
    r"^(\d{2}-[A-Za-z]{3}-\d{4})\s+(EMI (?:PRIN FOR|INT-).+?)\s+\(\d{3}/\d{3}\)\s+"
    r"([\d,]+\.\d{2})\s*(Cr)?$"
)
_KOTAK_FEE_LINE = re.compile(
    r"^(\d{2}-[A-Za-z]{3}-\d{4})\s+(.+?)\s+([\d,]+\.\d{2})\s*(Cr)?$"
)


def extract_kotak_transactions(raw_text: str) -> list[dict]:
    """Parse raw Kotak statement text into transaction dicts.

    Returns dicts with keys: date, description, category, amount, is_credit.
    See module note above for why "(Convert To EMI)" purchase lines are
    excluded in favor of their EMI PRIN/INT sub-lines, and "EMI CONV"
    reversal lines are dropped entirely.
    """
    rows = []
    section = None
    for line in raw_text.splitlines():
        line = line.strip()
        if not line:
            continue
        if "Purchases made in this cycle" in line:
            section = "purchases"
            continue
        if line.startswith("EMI & Loans"):
            section = "emi"
            continue
        if line.startswith("Other fees and charges"):
            section = "fees"
            continue
        if line.startswith("Total Fees & Charges") or line.startswith("EMI Snapshot"):
            section = None
            continue

        if section == "purchases":
            m = _KOTAK_PURCHASE_LINE.match(line)
            if not m:
                continue
            date_str, description, converted_to_emi, category, amount_str, cr = m.groups()
            if converted_to_emi:
                continue
            rows.append({
                "date": date_str,
                "description": description.strip(),
                "category": category.strip(),
                "amount": amount_str,
                "is_credit": bool(cr),
            })
        elif section == "emi":
            if _KOTAK_EMI_CONV_LINE.match(line):
                continue
            m = _KOTAK_EMI_INSTALMENT_LINE.match(line)
            if not m:
                continue
            date_str, description, amount_str, cr = m.groups()
            rows.append({
                "date": date_str,
                "description": re.sub(r"\s+", " ", description).strip(),
                "category": "EMI",
                "amount": amount_str,
                "is_credit": bool(cr),
            })
        elif section == "fees":
            m = _KOTAK_FEE_LINE.match(line)
            if not m:
                continue
            date_str, description, amount_str, cr = m.groups()
            rows.append({
                "date": date_str,
                "description": description.strip(),
                "category": "Fees",
                "amount": amount_str,
                "is_credit": bool(cr),
            })
    return rows


def kotak_transactions_to_md(rows: list[dict]) -> str:
    """Render extracted rows as the pipe-table parsers/kotak.py expects."""
    lines = [
        "| Date | Description | Amount (₹) |",
        "|---|---|---|",
    ]
    for r in rows:
        amount = r["amount"] + (" Cr" if r["is_credit"] else "")
        lines.append(f"| {r['date']} | {r['description']} | {amount} |")
    return "\n".join(lines)


def kotak_pdf_text_to_md(raw_text: str) -> str:
    """One-shot: raw extracted PDF text -> markdown parsers/kotak.py can parse."""
    return kotak_transactions_to_md(extract_kotak_transactions(raw_text))
