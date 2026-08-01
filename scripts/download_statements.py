"""
download_statements.py — Download bank/CC statement PDFs from Gmail into dump/<bank>/

Usage:
    python3 scripts/download_statements.py
    python3 scripts/download_statements.py --days 180    # look back 180 days (default 90)
    python3 scripts/download_statements.py --dry-run     # print what would be downloaded

First run: opens browser for Gmail OAuth consent. Token saved to token_gmail.json (gitignored).

Requirements (add to requirements.txt if missing):
    google-auth-oauthlib>=1.0.0
    google-api-python-client>=2.0
"""

import argparse
import base64
import os
import re
import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone

# ── Google API ────────────────────────────────────────────────────────────────
try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
except ImportError:
    print("Missing deps. Run:  pip install --break-system-packages google-auth-oauthlib google-api-python-client")
    sys.exit(1)

# ── Config ────────────────────────────────────────────────────────────────────
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
BASE_DIR = Path(__file__).resolve().parent.parent
DUMP_DIR = BASE_DIR / "dump"
TOKEN_FILE = BASE_DIR / "token_gmail.json"
CREDS_FILE = BASE_DIR / "gmail_oauth_creds.json"   # NOT the service account credentials.json

# Maps Gmail sender domain/pattern → subfolder name
SENDER_MAP = {
    "sbicard.com": "sbi",
    "Statements@sbicard.com": "sbi",
    "scapiacards@federalbank.co.in": "scapia",
    "icici.bank.in": "icici",
    "credit_cards@icici.bank.in": "icici",
    "cards@icici.bank.in": "icici",
    "rbl.bank.in": "rbl",
    "notification.my.rbl.bank.in": "rbl",
    "axis.bank.in": "axis",
    "statements@axis.bank.in": "axis",
    "kotak.bank.in": "kotak",
    "BankStatements@kotak.bank.in": "kotak",
    "creditcardalerts@kotak.bank.in": "kotak",
    "emiratesnbd.com": "emirates-nbd",
    "statement@emiratesnbd.com": "emirates-nbd",
}

# Gmail search query — statement emails with PDF attachments
GMAIL_QUERY = (
    "has:attachment filename:pdf "
    "("
    "from:sbicard.com OR "
    "from:scapiacards@federalbank.co.in OR "
    "from:icici.bank.in OR "
    "from:rbl.bank.in OR "
    "from:axis.bank.in OR "
    "from:kotak.bank.in OR "
    "from:emiratesnbd.com"
    ")"
)


def get_gmail_service():
    creds = None
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not CREDS_FILE.exists():
                print(f"ERROR: {CREDS_FILE} not found.")
                print("Create OAuth 2.0 credentials at https://console.cloud.google.com/")
                print("Download as credentials.json and place in the project root.")
                sys.exit(1)
            flow = InstalledAppFlow.from_client_secrets_file(str(CREDS_FILE), SCOPES)
            creds = flow.run_local_server(port=0)
        TOKEN_FILE.write_text(creds.to_json())
    return build("gmail", "v1", credentials=creds)


def sender_to_folder(sender: str) -> str | None:
    """Map a sender email to a dump subfolder name."""
    sender_lower = sender.lower()
    for pattern, folder in SENDER_MAP.items():
        if pattern.lower() in sender_lower:
            return folder
    # Fallback: try domain extraction
    match = re.search(r"@([\w.]+)>?$", sender_lower)
    if match:
        domain = match.group(1)
        for pattern, folder in SENDER_MAP.items():
            if domain in pattern.lower():
                return folder
    return None


def safe_filename(name: str) -> str:
    """Sanitize filename."""
    name = re.sub(r'[\\/*?:"<>|]', "_", name)
    return name.strip()


def download_statements(days: int = 90, dry_run: bool = False):
    service = get_gmail_service()
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y/%m/%d")
    query = f"{GMAIL_QUERY} after:{cutoff}"

    print(f"Searching Gmail: {query}\n")

    results = service.users().messages().list(userId="me", q=query, maxResults=100).execute()
    messages = results.get("messages", [])

    if not messages:
        print("No matching emails found.")
        return

    downloaded = 0
    skipped = 0
    errors = 0

    for msg_ref in messages:
        msg = service.users().messages().get(
            userId="me", id=msg_ref["id"], format="full"
        ).execute()

        headers = {h["name"]: h["value"] for h in msg["payload"].get("headers", [])}
        sender = headers.get("From", "")
        subject = headers.get("Subject", "no-subject")
        date_str = headers.get("Date", "")

        folder = sender_to_folder(sender)
        if not folder:
            continue

        dest_dir = DUMP_DIR / folder
        dest_dir.mkdir(parents=True, exist_ok=True)

        # Walk parts for PDF attachments
        parts = []
        payload = msg["payload"]
        if "parts" in payload:
            parts = payload["parts"]
            # Flatten nested parts
            queue = list(parts)
            parts = []
            while queue:
                part = queue.pop()
                if "parts" in part:
                    queue.extend(part["parts"])
                else:
                    parts.append(part)
        elif payload.get("mimeType", "").startswith("application"):
            parts = [payload]

        for part in parts:
            mime = part.get("mimeType", "")
            filename = part.get("filename", "")
            body = part.get("body", {})
            att_id = body.get("attachmentId")

            is_pdf = (
                mime in ("application/pdf", "application/octet-stream")
                or filename.lower().endswith(".pdf")
            )
            if not is_pdf or not att_id:
                continue

            # Build a clean filename: <date>_<original>
            try:
                parsed_date = datetime.strptime(
                    date_str[:25].strip(), "%a, %d %b %Y %H:%M:%S"
                )
                date_prefix = parsed_date.strftime("%Y-%m-%d")
            except Exception:
                date_prefix = "unknown-date"

            out_name = safe_filename(filename) if filename else f"{subject[:60]}.pdf"
            out_name = f"{date_prefix}_{out_name}"
            out_path = dest_dir / out_name

            if out_path.exists():
                print(f"  [skip] {folder}/{out_name}  (already exists)")
                skipped += 1
                continue

            print(f"  [{'DRY-RUN' if dry_run else 'download'}] {folder}/{out_name}")
            print(f"          from: {sender}")
            print(f"          subj: {subject}")

            if not dry_run:
                try:
                    att = service.users().messages().attachments().get(
                        userId="me", messageId=msg_ref["id"], id=att_id
                    ).execute()
                    data = base64.urlsafe_b64decode(att["data"])
                    out_path.write_bytes(data)
                    print(f"          saved: {len(data)//1024} KB")
                    downloaded += 1
                except Exception as e:
                    print(f"          ERROR: {e}")
                    errors += 1
            else:
                downloaded += 1

    print(f"\n{'DRY-RUN ' if dry_run else ''}Summary: {downloaded} downloaded, {skipped} skipped, {errors} errors")
    print(f"Statements in: {DUMP_DIR}")


def main():
    parser = argparse.ArgumentParser(description="Download bank statements from Gmail")
    parser.add_argument("--days", type=int, default=90, help="Look back N days (default 90)")
    parser.add_argument("--dry-run", action="store_true", help="List without downloading")
    args = parser.parse_args()
    download_statements(days=args.days, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
