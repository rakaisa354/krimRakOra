# n8n WF1 — Drive Statement → GitHub Parse

**Job:** Watch a Google Drive folder for new (encrypted) statement PDFs → trigger `finance.py parse --pdf` via GitHub Actions → confirm via Telegram.

n8n cannot execute Python. All parsing is delegated to GitHub Actions, which checks out the repo and runs `finance.py parse --pdf` against Google Sheets.

**Design note (2026-07-07):** n8n only ever sends a small JSON payload
(`repository_dispatch`'s `client_payload`, ~64KB limit) — it cannot carry the actual PDF
bytes. Two ways to bridge that: (A) n8n downloads the file and commits it into the repo before
dispatching, or (B) n8n sends just the Drive file ID and GitHub Actions downloads the PDF
itself. **Went with (B)** — real bank statements carry account numbers, PAN, GSTIN, and home
address; committing them into git (even a private repo) means that data sits in history
forever. GitHub Actions already has everything it needs to download the file directly: the
same service account `credentials.json` used for Sheets already requests the
`drive.readonly` scope in `sheets.py`'s `SCOPES` (previously unused). See
`scripts/download_drive_file.py`.

---

## Credentials Required

| Credential Name (n8n vault) | Type | Used by |
|---|---|---|
| `Google Drive OAuth` | OAuth2 | Drive Trigger |
| `GitHub PAT` | HTTP Header Auth | HTTP Request (GH dispatch) |
| `Telegram Bot` | Telegram API | Send Message node |

GitHub PAT minimum scopes: `repo` (for `repository_dispatch`).

**One-time setup**: share the watched Drive folder with the service account's email (found in
`credentials.json`'s `client_email` field) — Drive won't let the service account read files in
a folder it hasn't been granted access to, same as any other Drive share.

---

## Node Map

```
[Google Drive Trigger] → [Trigger GitHub Parse] → [Telegram Notify]
                                                 ↘ (error) → WF6
```

---

## Node 1 — Google Drive Trigger

| Field | Value |
|---|---|
| Node type | `n8n-nodes-base.googleDriveTrigger` |
| Trigger on | `specificFolder` |
| Folder to watch | Drive folder ID for `statements/` (paste folder ID, not name) |
| Event | `fileCreated` |
| Poll interval | Every 1 minute |
| Filter — MIME type | `application/pdf` (bank statements arrive as encrypted PDFs, not pre-converted markdown — Module 4 in `finance.py` does the decrypt/extract/convert) |

> **Tip:** Get the folder ID from the Drive URL: `https://drive.google.com/drive/folders/<FOLDER_ID>`

Output fields used downstream: `$json.name` (filename), `$json.id` (Drive file ID — this is
what GitHub Actions uses to pull the actual file, not n8n).

---

## Node 2 — Trigger GitHub Parse (HTTP Request)

Fires a `repository_dispatch` event carrying only the file ID + filename (small JSON — no PDF
bytes). GitHub Actions picks this up, downloads the real file from Drive, then runs
`finance.py parse --pdf`.

| Field | Value |
|---|---|
| Method | `POST` |
| URL | `https://api.github.com/repos/rakaisa354/krimRakOra/dispatches` |
| Authentication | Generic Credential → `GitHub PAT` (Header Auth) |
| Header name | `Authorization` |
| Header value | `Bearer <PAT>` |
| Additional header | `Accept: application/vnd.github+json` |
| Body (JSON) | See below |

```json
{
  "event_type": "parse-statement",
  "client_payload": {
    "file_id": "={{ $json.id }}",
    "filename": "={{ $json.name }}"
  }
}
```

**Why not parse in n8n?**  
n8n has no Python runtime. `finance.py parse` requires `gspread`, `anthropic`, `pypdf`, and
local config. GitHub Actions provides the full Python environment via the repo's workflow
`parse-statement.yml`, which already has all secrets wired.

---

## Node 3 — Telegram Notify

| Field | Value |
|---|---|
| Node type | `n8n-nodes-base.telegram` |
| Operation | `sendMessage` |
| Chat ID | Your personal Telegram chat ID — hardcode it or reference an n8n **Variable** (`{{ $vars.TELEGRAM_CHAT_ID }}`). n8n Cloud has no environment-variable support in expressions (`$env` doesn't resolve) — only the Variables feature (`$vars`) or a literal value work. |
| Text | `📥 Statement received: {{ $('Google Drive Trigger').first().json.name }} — parsing started` |

---

## Error Workflow

In **WF1 Settings → Error Workflow**: select `WF6 — Error Handler`.

This covers failures in both the HTTP Request node (GH API down, bad PAT) and the Telegram node.

---

## GitHub Actions Side

`.github/workflows/parse-statement.yml` already exists and handles more than just the n8n
trigger — it also supports a manual `workflow_dispatch` (for testing) and a `push` trigger for
`statements/*.md` files, with Telegram success/failure notifications and a webhook callback to
archive the source file in Drive after a successful parse. The n8n-triggered path
(`repository_dispatch`) specifically:

```yaml
- name: Download statement from Drive (n8n trigger)
  if: github.event_name == 'repository_dispatch'
  run: |
    python3 scripts/download_drive_file.py \
      --file-id "${{ github.event.client_payload.file_id }}" \
      --out "incoming/${{ github.event.client_payload.filename }}"

- name: Parse statement (n8n trigger)
  if: github.event_name == 'repository_dispatch'
  run: |
    FILE="${{ github.event.client_payload.filename }}"
    python3 finance.py parse --pdf "incoming/$FILE"
```

A final `Clean up downloaded statement and credentials` step (`if: always()`) removes
`incoming/`, `credentials.json`, and `.env` regardless of success or failure — the runner is
ephemeral and destroyed after the job anyway, but this is explicit rather than relying on that.

**Secrets required** (GitHub repo → Settings → Secrets and variables → Actions):
`GOOGLE_CREDENTIALS_JSON` (the service account JSON, same one used locally), `GOOGLE_SHEETS_ID`,
`CLAUDE_API_KEY`, `FX_API_KEY`, `CARD_PASSWORDS`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, and
`N8N_ARCHIVE_WEBHOOK_URL` (for the post-parse Drive-archive callback).

---

## Verification

1. Upload a test encrypted statement PDF to the watched Drive folder.
2. Within 1 min, the n8n execution log should show WF1 triggered.
3. Check GitHub → Actions tab: a `parse-statement` run should appear, with the "Download
   statement from Drive" step succeeding (confirms the service account can read the file —
   if it fails here, the Drive folder likely hasn't been shared with the service account
   email yet).
4. After the run completes, verify new rows in the **Transactions** Google Sheet with
   today's date.
5. Verify Telegram message: `📥 Statement received: <filename> — parsing started` (from n8n)
   followed by `✅ Statement parsed and written to Sheets.` (from GitHub Actions).
6. Check n8n execution history — all 3 nodes should show green.
