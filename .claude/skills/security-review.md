# Skill: security-review

Run this skill after completing any implementation phase to verify the codebase has no security regressions.

## Steps

1. **Secret leak check** — grep for hardcoded credentials:
   ```bash
   grep -rn "sk-ant\|AIza\|ghp_\|AKIA\|Bearer \|password\s*=\|api_key\s*=" \
     --include="*.py" --include="*.json" --include="*.sh" \
     --exclude-dir=".git" --exclude-dir="venv" .
   ```
   Expected: zero matches. If any found, move to `.env` immediately.

2. **gitignore coverage** — confirm sensitive files are ignored:
   ```bash
   git check-ignore -v .env credentials.json "*.pdf" "statements/"
   ```
   All four must be listed as ignored. Add any missing entries to `.gitignore`.

3. **Claude API call audit** — confirm merchant-only payloads:
   - Open `categorizer.py` → inspect `prompt` construction.
   - The `merchant_lines` string must contain ONLY `merchant | amount currency` — no raw statement text, no card numbers, no full descriptions.

4. **Sheets scope check** — `sheets.py` SCOPES list:
   - Must contain `spreadsheets` (read/write).
   - Must NOT contain `drive` write scope (`drive` is acceptable only as `drive.readonly`).

5. **Telegram webhook** — in WF2 n8n workflow JSON:
   - Confirm `"headerAuth"` or `"secret"` field is set on the Webhook node.
   - Value must reference an n8n credential, not a hardcoded string.

6. **Dead-letter check** — WF6 dead-letter writes go to Google Drive, not a public bucket.

## Pass criteria
All 6 checks pass with zero findings → log "✓ security-review passed" in the plans directory:
```bash
echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) security-review PASSED" \
  >> docs/superpowers/plans/security-log.txt
```

If any finding: fix before proceeding to next phase.
