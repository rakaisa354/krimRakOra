"""Download a file from Google Drive by ID, for use inside GitHub Actions.

Reuses the same service account credentials.json + drive.readonly scope
already declared in sheets.py's SCOPES (unused there today). This lets the
`parse-statement` GH Actions workflow pull an encrypted statement PDF
straight from Drive into the ephemeral runner's filesystem — the PDF is
never committed to git, only ever touches disk for the lifetime of the job.
"""

import argparse
import io
import os
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]


def download_file(file_id: str, out_path: str) -> str:
    creds = Credentials.from_service_account_file("credentials.json", scopes=SCOPES)
    service = build("drive", "v3", credentials=creds)
    request = service.files().get_media(fileId=file_id)

    out_dir = os.path.dirname(out_path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    with io.FileIO(out_path, "wb") as fh:
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()

    return out_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download a Drive file by ID.")
    parser.add_argument("--file-id", required=True, help="Google Drive file ID")
    parser.add_argument("--out", required=True, help="Local output path")
    args = parser.parse_args()

    path = download_file(args.file_id, args.out)
    print(f"✓ Downloaded → {path}")
