# krimRakOra — Personal Financial Controller

> **TL;DR for Claude**: Personal finance automation for an India-based user in debt-kill phase. Tracks every rupee across 4+ credit cards using Python parsers → Google Sheets → n8n → Telegram bot. Always INR-first, multi-currency capable. Read this file fully before touching any code.

---

## Current Status (as of 2026-08-02)

| Phase | Status | What's done |
|---|---|---|
| Phase 0 — Setup | ✅ Done | Git, .env, .gitignore, Google Sheets 9 tabs created |
| Phase 1 — Parsers | ✅ Done | ICICI, RBL, SBI, Scapia, Kotak parsers + tests |
| Phase 1.5 — PDF Decryption (Module 1) | ✅ Done | `pdf_decrypt.py` + `finance.py decrypt` command, tested against real ICICI statement |
| Phase 1.6 — PDF-to-md extractors (Module 2/3) | ✅ Done for all cards in scope | icici/rbl/sbi/scapia/kotak done + verified against real statements (57 pdf_to_md tests, all passing). Axis and Emirates NBD dropped — see below |
| Phase 1.7 — Wire extractors into CLI (Module 4) | ✅ Done | `finance.py parse --pdf <file>` now goes straight from an encrypted statement PDF to Sheets in one command, for all 5 in-scope banks |
| Phase 2 — n8n WF1 | ✅ Verified end-to-end 2026-08-02 | Real statement PDF → Drive → n8n → GitHub Actions → decrypt/parse → 60 real rows written to Transactions sheet → truthful "✅ parsed" Telegram message. Live workflow id is `yO2jvG2di7fSeAz0` (NOT `NIwD3iarrxwH36qj` — see `## Session: 2026-08-02`). WF2 (Telegram agent) still not started. |
| Phase 3 — n8n WF3+WF4+WF5 | ❌ Not started | Skills written |
| Phase 4 — Debt + Net Worth | ✅ Done | `debt_planner.py`, `net_worth.py`, `report.py` written + wired |
| Phase 5 — Hardening | ✅ Done | 87/87 tests pass; test_sheets flake fixed (see below) |

### Axis and Emirates NBD — dropped from scope
Axis: the only files under `dump/axis/` are savings-account statements (zero transactions,
opening balance = closing balance) and a Kotak CC application form got mixed in during
inspection — there is no actual Axis credit card in use. User confirmed no Axis credit card
exists right now; revisit only if one gets opened in future.
Emirates NBD: user confirmed not required, skipped without investigation.
Kotak **does** have a real credit card (Cashback+ X8502) — parser/extractor built and verified,
see below.

### Immediate next action
> **Superseded 2026-08-01** — this section reflects the 2026-07-08 state, written when Phase 2
> hadn't started yet. Phase 2 (WF1) has since been built, broken, and mostly re-fixed — see
> `## Session: 2026-08-01` at the end of this file for what actually happened and what to do
> next. Left below as historical record, per the project's own "mention, don't delete"
> Surgical Changes rule.

**Module 4 is done.** `finance.py parse` now accepts `--pdf <file>` as an alternative to
`--file <md>`: it decrypts, extracts raw text, detects the bank from the raw PDF text (the
same keyword strings `parsers/__init__.py`'s `detect_card_type` already uses — "ICICI Bank",
"RBL Bank", "SBI Card", "Scapia"/"Federal", "Kotak Mahindra Bank" — all appear verbatim in the
raw PDF text too, confirmed against real statements), converts via the matching
`pdf_to_md.py` function, and parses directly with the already-known bank's parser (see
`PARSERS` in `parsers/__init__.py`) rather than re-running `detect_card_type` on the generated
markdown — that markdown is a bare pipe table with no bank-name header line, so re-detecting
on it always failed (caught this as a real bug during verification, not just theoretical).
Verified end-to-end (decrypt → extract → detect → convert → parse, with Sheets/Claude API
mocked) against one real statement per bank for all 5 in-scope cards — all produced sane
transaction rows.

**Next up: Phase 2 (n8n WF1)**. WF1 can now call `finance.py parse --pdf <file>` directly
instead of expecting a pre-converted `.md` file from Drive — one command takes a bank
statement PDF straight to a Sheets write. See the `n8n-wf1-statement-ingestion` skill for the
workflow runbook.

### Environment note (fixed 2026-07-06)
Project folder lives under `~/Documents/...` which has iCloud "Desktop & Documents Folders"
sync ON. This caused severe slowness (pytest 71s for 3 trivial tests, PDF decrypt hangs,
`import anthropic` stalling) because iCloud lazily fetches files on access. **Fix applied:**
venv moved out of the synced folder to `~/venvs/krimRakOra`. Always activate with:
```bash
cd "~/Documents/02_Personal/Claude Projects/krimRakOra"
source ~/venvs/krimRakOra/bin/activate
```
Do NOT recreate `venv/` inside the project folder — it will reintroduce the slowness.

---

## Stack (quick ref)
| Layer | Tool |
|---|---|
| Automation | n8n Cloud (6 workflows) |
| Interface | Telegram Bot |
| Storage | Google Sheets (9 tabs) |
| File input | Google Drive (MD uploads) |
| AI brain | Claude API — `claude-haiku-4-5-20251001` for categorization |
| Local CLI | `python finance.py` (4 commands) |
| FX | exchangerate-api.com |

---

## Google Sheets (9 tabs) — all created ✅
`Income` · `Transactions` · `Debts` · `Budget` · `Goals` · `Net_Worth` · `FX_Rates` · `Categories` (57 rows seeded) · `Vendor_Map`

---

## Transaction schema (unified output of all parsers)
```
date | card_account | merchant | amount | currency | exchange_rate | amount_inr
| category | subcategory | budget_type | payment_method | notes
```

---

## Budget split (debt-kill phase)
`need` 40% · `debt` 30% · `save` 20% · `want` 10%  
(budget_type values in Transactions sheet use lowercase: need/debt/save/want/petty)

---

## Key files
| File | Role |
|---|---|
| `finance.py` | CLI entry — commands: `parse` (`--file` or `--pdf`), `decrypt`, `debt`, `worth`, `report` |
| `config.py` | All env vars loaded from `.env` |
| `sheets.py` | `get_sheet()`, `append_rows()`, `read_all()` |
| `fx.py` | `get_rate()`, `convert_to_inr()` |
| `categorizer.py` | Layer 1: Vendor_Map prefix → Layer 2: Claude batch (1 call per run) |
| `parsers/__init__.py` | Card detection router |
| `parsers/icici.py` | ICICI Amazon Pay |
| `parsers/rbl.py` | RBL Bank — CR suffix + foreign currency |
| `parsers/sbi.py` | SBI Card — C/D/M suffixes, FlexiPay |
| `parsers/scapia.py` | Scapia Federal — strips Coins col |
| `parsers/kotak.py` | Kotak Mahindra Bank — Cr suffix for credits/payments |
| `debt_planner.py` | Hybrid avalanche+snowball — `load_debts()`, `run_avalanche()`, `print_plan()` |
| `net_worth.py` | Monthly snapshot — `snapshot()` Click command |
| `report.py` | Monthly report — `report()` Click command + Drive upload |
| `pdf_decrypt.py` | Module 1 — `decrypt_pdf()` tries `CARD_PASSWORDS` from `.env`, `extract_text()` for downstream use. Pure-Python (pypdf + cryptography), no third-party API. |
| `pdf_to_md.py` | Module 2/3 — raw `extract_text()` output → pipe-table markdown each `parsers/*.py` expects. One `extract_<bank>_transactions()` + `<bank>_pdf_text_to_md()` pair per issuer. Done: icici, rbl, sbi, scapia, kotak. Axis/emirates-nbd dropped (see status table). Wired into `finance.py`'s `parse --pdf` (Module 4). |
| `scripts/setup_sheets.py` | Idempotent 9-tab setup + Categories seed |
| `scripts/query_budget.py` | Month spend summary (used by Telegram WF2) |
| `scripts/quick_add.py` | Quick-add a transaction |
| `scripts/sync_fx.py` | Fetch + write today's FX rates |

---

## CLI commands (all working)
```bash
python finance.py parse --file statements/ICICI_Bank.md
python finance.py parse --file statements/ICICI_Bank.md --dry-run
python finance.py parse --pdf dump/icici/statement.pdf          # Module 4 — decrypt+extract+parse in one step
python finance.py parse --pdf dump/kotak/statement.pdf --dry-run
python finance.py debt                          # avalanche plan
python finance.py debt --extra 5000             # with extra monthly payment
python finance.py worth                         # net worth snapshot (interactive)
python finance.py report --month 2026-05 --dry-run
python finance.py report --month 2026-05        # + uploads to Drive
python finance.py decrypt --file dump/icici/statement.pdf   # Module 1 — outputs *_decrypted.pdf

python3 scripts/setup_sheets.py                 # idempotent sheet setup
python3 scripts/sync_fx.py                      # FX sync
python3 scripts/query_budget.py --month 2026-06
python3 scripts/quick_add.py --merchant "Zomato" --amount 350
```

---

## n8n Workflows (Phase 2+)
- **WF1** Drive → GH Actions `parse-statement` → `finance.py parse` → Sheets
- **WF2** Telegram AI Agent (Claude haiku, memory, quick-add, queries)
- **WF3** Daily FX sync 6am IST (cron `30 0 * * *`)
- **WF4** Daily spend summary 9pm IST (cron `30 15 * * *`)
- **WF5** Monthly report 1st of month 8am IST (cron `30 2 1 * *`)
- **WF6** Error handler — 3x retry, dead-letter to Drive, Telegram alert
- Draft JSONs: `WF1 — Drive Statement → GitHub Parse.json`, `WF2 — Telegram AI Agent.json`

---

## Coding conventions
- All amounts stored as **float** INR. Foreign → `convert_to_inr()` before write.
- Dedup key: `(date, merchant, amount_inr)` — checked before every Sheets write.
- Claude API: send **merchant + amount only**. Model: `claude-haiku-4-5-20251001`.
- Retry: 4 attempts, 60s·120s·180s·240s on `RateLimitError`.
- Confidence threshold: <80% → flag for review.
- `.env` + `credentials.json` are gitignored. Never hardcode secrets.

---

## Dependencies (requirements.txt)
```
pandas>=2.2, gspread==6.1.2, anthropic>=0.50.0, httpx>=0.23.0,<0.28.0,
click==8.1.7, python-dotenv==1.0.1, pytest==8.2.0, google-auth==2.29.0,
requests>=2.31, python-dateutil>=2.9, google-api-python-client>=2.0,
pypdf>=4.0, cryptography>=41.0
```

---

## Test suite
```bash
python -m pytest tests/ -q   # 87 tests total, all passing
```
**test_sheets flake — fixed 2026-07-08.** `tests/test_fx.py` did `sys.modules['sheets'] =
MagicMock()` at import time to stub `sheets.read_all` before importing `fx`, but never
restored `sys.modules['sheets']` afterward. Since `sys.modules` is process-global, every test
file collected after `test_fx.py` in the same pytest run — including `test_sheets.py` — then
imported the fake `MagicMock` in place of the real `sheets` module. `test_sheets.py`'s
monkeypatch of `sheets.get_sheet` was silently patching an attribute on the mock instead of the
real module, so the real `append_rows()` never ran and `captured` stayed empty. Reproducible
only when run as part of the full suite (`pytest tests/`), not standalone — which is exactly
why it looked "flaky." Fix: `test_fx.py` now saves the real `sheets` module (if already
imported) before swapping in the mock, and restores it (or deletes the key) right after
`from fx import ...` completes.
- `tests/test_icici.py` — 4 tests ✅
- `tests/test_rbl.py` — 9 tests ✅
- `tests/test_sbi.py` — 7 tests ✅
- `tests/test_scapia.py` — 7 tests ✅
- `tests/test_kotak.py` — 7 tests ✅
- `tests/test_fx.py` — ✅
- `tests/test_sheets.py` — `test_append_rows_calls_api` ✅ (re-verified 2026-08-01: full suite green,
  including `test_fx.py` running before `test_sheets.py` in the same session — the exact collection
  order that used to trigger the flake. Stale "still open" note removed; the 2026-07-08 fix holds.)
- `tests/test_pdf_to_md.py` — 7 tests ✅ (icici extractor)
- `tests/test_rbl_pdf_to_md.py` — 9 tests ✅ (rbl extractor)
- `tests/test_sbi_pdf_to_md.py` — 9 tests ✅ (sbi extractor)
- `tests/test_scapia_pdf_to_md.py` — 9 tests ✅ (scapia extractor)
- `tests/test_kotak_pdf_to_md.py` — 7 tests ✅ (kotak extractor)
- axis/emirates-nbd — dropped from scope, no tests planned

---

## Skills Index (19 skills in `.claude/skills/`)
> Invoke: *"run the `<skill-name>` skill"*

### Quality & Review
| Skill | When |
|---|---|
| `security-review` | After each phase |
| `code-review` | After any script |

### CC Parsers
| `add-parser` | New credit card |

### Python Scripts
| `debt-plan` | debt_planner.py spec |
| `net-worth` | net_worth.py spec |
| `monthly-report` | report.py spec |
| `sheets-setup` | setup_sheets.py |
| `dedup-stress-test` | idempotency tests |

### n8n Workflows
| `n8n-wf1-statement-ingestion` | WF1 runbook |
| `n8n-wf2-telegram-agent` | WF2 runbook |
| `n8n-wf3-fx-sync` | WF3 runbook |
| `n8n-wf4-daily-summary` | WF4 runbook |
| `n8n-wf5-monthly-report` | WF5 runbook |
| `n8n-wf6-error-handler` | WF6 runbook |

### Operations
| `vendor-map-train` | Vendor_Map curation |
| `budget-check` | Budget interpretation |
| `goal-track` | Goals management |
| `onboard-new-month` | Monthly ritual |

### Behavior
| `karpathy-guidelines` | Coding discipline (see below) |

### External tooling (installed globally, see below)
| `gstack` | YC-style workflow specialists — see gstack section |
| `claude-mem` | Persistent cross-session memory — see claude-mem section |

---

## gstack
Use /browse from gstack for all web browsing. Never use mcp__claude-in-chrome__* tools.
Available skills: /office-hours, /plan-ceo-review, /plan-eng-review, /plan-design-review,
/design-consultation, /design-shotgun, /design-html, /review, /ship, /land-and-deploy,
/canary, /benchmark, /browse, /open-gstack-browser, /qa, /qa-only, /design-review,
/setup-browser-cookies, /setup-deploy, /setup-gbrain, /sync-gbrain, /retro, /investigate,
/document-release, /document-generate, /codex, /cso, /autoplan, /pair-agent, /careful, /freeze,
/guard, /unfreeze, /gstack-upgrade, /learn.

Useful for this project: `/review` before committing parser/sheets changes, `/cso` for the
Phase 5 security-hardening pass, `/ship` once n8n workflows (Phase 2+) are ready to PR.

## claude-mem
Persistent memory across Claude Code sessions for this project (installed globally via
`npx claude-mem install`). Automatically captures session activity, compresses it, and
injects relevant context into future sessions — no manual action needed. Search past
context with the `mem-search` skill or the web viewer at http://localhost:37777.

---

## Coding discipline (Karpathy guidelines)
> Source: https://github.com/multica-ai/andrej-karpathy-skills — merged as project-wide behavioral rules.

**1. Think Before Coding** — State assumptions explicitly; if uncertain, ask. Present multiple interpretations rather than picking silently. Push back if a simpler approach exists. Stop and name what's unclear rather than guessing.

**2. Simplicity First** — Minimum code that solves the problem. No speculative features, unused abstractions, or unrequested configurability. If 200 lines could be 50, rewrite it.

**3. Surgical Changes** — Touch only what the task requires. Don't refactor or "improve" adjacent code/comments/formatting. Match existing style. Remove only the dead code your own change orphaned — mention, don't delete, pre-existing dead code. Every changed line should trace to the user's request.

**4. Goal-Driven Execution** — Turn imperative asks into verifiable goals ("fix the bug" → "write a failing test, then make it pass"). For multi-step tasks, state a brief plan with a verify step per item.

**Tradeoff:** biases toward caution over speed — use judgment on trivial tasks (typo fixes, obvious one-liners).

---

## Security non-negotiables
1. Strip full statement text before Claude API call.
2. Service account = least-privilege.
3. Validate Telegram webhook secret on every n8n request.
4. Run `security-review` skill after each phase.

---

## PDF ingestion micro-project (2026-07-06)

### Decision: rejected the Supabase/LlamaParse/Next.js pivot
A proposal was floated to rebuild ingestion on Cowork → FastAPI decrypt microservice →
LlamaParse/OpenAI extraction → Supabase → LangChain SQL agent → Next.js/Vercel frontend.
**Rejected** — red-teamed and decided against, for these reasons:
- User is in debt-kill phase and wants **zero new recurring cost**. LlamaParse, OpenAI
  extraction, Supabase, Vercel all introduce paid usage; the existing stack (Sheets, n8n
  Cloud free tier, Telegram) is free and already built.
- Shipping full bank/CC statements to third-party APIs (LlamaParse, OpenAI) violates the
  existing security non-negotiable above ("strip full statement text before Claude API call").
- Duplicates already-built, tested work: 4 parsers with 35/36 tests passing already solve
  extraction; Sheets is already the DB; Telegram (WF2) is already the planned interface.
- Text-to-SQL agents (Module 4 of the rejected plan) are a real risk of destructive/wrong
  queries against a live financial DB.
- **Kept from the proposal:** the micro-module execution discipline (one module at a time,
  stop and test before proceeding) — matches the existing Karpathy "goal-driven execution" rule.

### Approved direction instead
Close the one real gap (statements arrive as **password-protected PDFs**, but parsers expect
markdown/text) by extending the existing free stack, not replacing it:
- **Module 1 — PDF Decryption** ✅ DONE. `pdf_decrypt.py`, `finance.py decrypt` command.
  Verified against a real AES-256-encrypted ICICI statement (`dump/icici/2026-06-10_94847143.pdf`,
  password `rake3012` from `CARD_PASSWORDS` in `.env`).
- **Module 2/3 — PDF-to-md extractors** ✅ DONE for all cards in scope. `pdf_to_md.py`. One
  extractor per issuer, each built and verified against a real decrypted statement (not just a
  synthetic fixture) before moving to the next, per the micro-module rule. Pure regex, reuses
  each existing `parsers/*.py` as the downstream consumer — no LlamaParse/OpenAI/third-party API.
  - `icici` ✅ — anchors on `DATE SERNO`, takes the *last* reward/amount match in each blob to
    survive chart-legend text bleeding in after the amount.
  - `rbl` ✅ — one line per transaction; raw text drops the "CR" credit marker the PDF shows
    visually, so credits (PAYMENT/CASHBACK/TRANSFERRED TO EMI/REFUND/REVERSAL) are detected by
    keyword instead. Also normalizes `CCY( AMT )` → `(CCY AMT)` for `parsers/rbl.py`'s
    FOREIGN_PATTERN.
  - `sbi` ✅ — one line per transaction ("DD Mon YY DESC AMOUNT [C|D|M]"); IGST lines on EMI
    instalments print with no date of their own (PDF sub-line), attached to the prior
    transaction's date via a narrow `^IGST` match (a generic dateless-line fallback would have
    false-matched the statement's T&C/footer sections, which are full of unrelated decimal
    numbers).
  - `scapia` ✅ — anchors on `DATE·TIME`; raw text has no spaces within a single PDF text run
    (merchant names run together), wraps long merchant names onto their own line before the
    amount, and interleaves a repeated page-header block at every page break — same
    take-the-match-in-blob strategy as icici handles all three. The "YourEMItransactions"
    section (monthly instalment breakdown of already-counted spend) is deliberately excluded,
    same reasoning as icici's Amortization SKIP_PATTERNS.
  - `kotak` ✅ — one line per transaction. Real statement (Cashback+ Credit Card X8502) revealed
    a subtlety the other issuers don't have: purchases tagged `(Convert To EMI)` are reversed in
    the SAME statement by a matching `EMI CONV <merchant>(NNN) <same amount> Cr` line, and only
    the `EMI PRIN FOR ...` + `EMI INT-...` sub-lines are real new spend for the cycle — verified
    against the statement's own printed "Total Purchases" and "Total Amount Due" totals (exact
    match, ₹1,980.72). This is the opposite of icici/scapia's EMI handling, where the full
    purchase is counted once at the time of purchase and the EMI breakdown is pure
    administration — don't assume all EMI sections follow the same rule, verify against the
    statement's own totals every time.
  - `axis`, `emirates_nbd` — dropped from scope (see status table above). No parser built.
- **Module 4 — wiring extractors into the CLI** ✅ DONE. See "Immediate next action" above.

### Working notes for extractor development (apply to any future new-card work)
- PDF files under `dump/` sit in an iCloud-synced folder inside this sandbox; `mcp__workspace__bash`
  hits `OSError: Resource deadlock avoided` on files iCloud hasn't fetched locally yet. Fix: `Read`
  the file once (even though PDF read-as-image fails on an encrypted PDF, the fetch still warms
  it) — then the same bash `decrypt_pdf()` / `extract_text()` call succeeds. This applies to
  *any* project file, not just PDFs — `parsers/*.py`, `pdf_to_md.py`, `config.py`, test files,
  etc. all hit the same deadlock the first time a bash call touches them in a session; `Read`
  each one (an `offset`/`limit` read is enough to warm it) before running pytest.
- Not every card uses the same password set. Scapia needed 4 new passwords added to
  `CARD_PASSWORDS` beyond the original ICICI/RBL/SBI set; axis and kotak each needed one more
  beyond that. Check `dump/<bank>/decrypt_icici.py`-style one-offs if they exist for a bank
  (none currently do besides icici's).
- A filename alone doesn't guarantee the file is a credit card statement — check the extracted
  text before building anything. The Axis dump turned out to be savings-account statements
  (opening balance = closing balance, zero transactions) despite being named like CC statements,
  and one Kotak file was a credit card *application form*, not a statement. Always print the
  first ~1500 chars of `extract_text()` output and confirm it has real transaction rows,
  Minimum Amount Due, a billing cycle, etc. before writing a parser.
- Always build the pytest fixture from a **verbatim excerpt of the real extracted text**, not a
  clean hand-written approximation — every real edge case found so far (RBL's missing CR marker,
  SBI's dateless IGST line, Scapia's page-header bleed, Kotak's EMI-conversion-nets-to-zero
  accounting) would have been invisible with a tidy synthetic fixture.
- When a statement has an EMI/instalment section, don't assume it works like the last card you
  built — verify the extracted total against the statement's own printed totals (Total
  Purchases, Total Amount Due) every time. Kotak's EMI accounting is the exact opposite of
  icici/scapia's.

### Relevant real files found during this work
`dump/` contains raw encrypted statement PDFs for icici, rbl, sbi, scapia, kotak, axis,
emirates-nbd. Axis and emirates-nbd are out of scope (see status table). `dump/icici/decrypt_icici.py`
and `dump/icici/convert_to_md.py` are prior one-off manual scripts (password `rake3012` hardcoded)
that `dump/icici/staging/*.md` was generated from — useful reference, superseded by `pdf_to_md.py`
for icici specifically.

### Note for next session
Parser + extractor + CLI wiring work for all in-scope cards (icici, rbl, sbi, scapia, kotak) is
done and tested: `finance.py parse --pdf <file>` goes straight from an encrypted statement PDF
to a Sheets write.

**Phase 2 (n8n WF1) — code/config done, live workflow import pending on user.** Discovered the
live n8n instance already has an active `WF1 — Drive Statement → GitHub Parse` workflow
(id `NIwD3iarrxwH36qj`) implementing a different design (Option A: downloads the file from
Drive, base64-encodes it, and commits it into the repo's `statements/` folder via GitHub's
Contents API) than what we designed here (Option B: n8n sends only the Drive file ID, GitHub
Actions downloads the PDF itself — no statement PDF ever touches git, given real statements
carry account numbers/PAN/GSTIN/address). Rewrote `WF1 — Drive Statement → GitHub Parse.json`
to Option B and updated `.github/workflows/parse-statement.yml`'s n8n-triggered path to
download via the new `scripts/download_drive_file.py` (reuses the same service account
`credentials.json` already used for Sheets — its `drive.readonly` scope in `sheets.py` was
already declared but unused until now) then call `finance.py parse --pdf`. Tried pushing this
live via `mcp__n8n__update_workflow` — failed with `settings must NOT have additional
properties`, looks like an n8n MCP connector bug against this n8n Cloud version (2.27.5), not a
problem with the workflow content (failed identically regardless of payload). **User imported
the updated JSON manually** in the n8n UI instead — done.

**Mistakes caught by the user after import, both fixed**:
1. The draft JSON's Telegram Notify node used `{{ $env.TELEGRAM_CHAT_ID }}` — **wrong**, n8n
   Cloud has no environment-variable support in expressions (`$env` doesn't resolve there,
   despite being valid on self-hosted n8n). User fixed it live to use n8n's Variables feature
   instead. Draft JSON now hardcodes `chatId: "832207392"` (matching the existing convention
   already used in `KRIMRAK_ORA — WF-01a-CALLBACK Statement Processor`'s Telegram node) so it
   doesn't drift from what's actually live again. **Rule for future n8n work in this project**:
   never use `$env.*` in an n8n Cloud expression — use `$vars.*` (n8n's Variables feature,
   configured in n8n UI → Settings → Variables) or hardcode the value.
2. The draft JSON had no sticky-note documentation on the canvas — inconsistent with this n8n
   instance's own convention (e.g. the KDIQ workflow family always opens with a "Setup Notes"
   sticky note covering job/design-decisions/credentials). Added one to WF1 covering the same:
   job description, the Option A vs B rationale, the n8n Cloud `$env` gotcha, the one-time
   Drive-folder-sharing step, and which credential goes on which node.

Once live: confirm the Drive folder (id `1enRhFKT8-0jT_JHbzA1i5DzJwDTbGlgs`) is shared with the
service account's email, and add the 5 required GH Actions secrets if not already present
(`GOOGLE_CREDENTIALS_JSON`, `GOOGLE_SHEETS_ID`, `CLAUDE_API_KEY`, `FX_API_KEY`,
`CARD_PASSWORDS` — `TELEGRAM_BOT_TOKEN`/`TELEGRAM_CHAT_ID`/`N8N_ARCHIVE_WEBHOOK_URL` already
used by the pre-existing workflow steps). Then run the Verification checklist in the
`n8n-wf1-statement-ingestion` skill.

**Also investigated this session**: a separate, older `KRIMRAK_ORA` workflow family exists in
the same n8n instance (`WF-01a-TRIGGER-{RBL,SBI,SCAPIA}`, Statement Detector, Callback
Statement Processor, Classification Engine, Debt Avalanche Engine, Petty Cash Ingestion) —
created/touched May 10–24, i.e. before this project's WF1/WF2 and Python modules (all June 1+).
Confirmed it's an earlier prototype, not something currently relied on: it sends full statement
PDFs directly to Claude's document API (conflicts with this project's "strip full statement
text before Claude API call" rule) and writes to a different Google Sheet
(`KRIMRAK_ORA_Master`, not the 9-tab sheet this project uses). Its ideas (scheduled
classification, debt engine) are already superseded by the tested, simpler `categorizer.py` /
`debt_planner.py` in this repo. Left untouched, not migrating anything from it — flagged here
so a future session doesn't get confused finding both. Also note: **do not confuse this with
KRIMRAK_ORA workflows** if browsing the n8n instance — filter by the "KRIMRAK" team project and
the `WF1`/`WF2` naming (this project) vs `KRIMRAK_ORA —` prefix (the old one).

---

## Session: 2026-08-01 — WF1 debugging & git recovery

### Started with an LLM council run
Ran the `llm-council` skill (5 independent advisors → peer review → chairman synthesis) against
the whole project. Verdict: fix the `test_sheets.py` flake note (done, see above), then actually
**verify WF1 end-to-end for real** before building anything else — the 2026-07-08 note above
claimed Phase 2 was "code/config done, live import pending," which turned out to be optimistic
(see below). Order after that: WF3 → WF4/WF5 → WF2 last. Financial data connectors (Plaid-style)
and Cowork's "finance"/"financial-analysis" plugins were both evaluated and **rejected** —
they're shaped for corporate/investment-banking use, not personal debt tracking, and add
recurring cost/third-party data exposure this project has already rejected once (see the
Supabase/LlamaParse pivot rejection above). No change from that decision.

### Finding 1: WF1 was not actually what CLAUDE.md said it was
Checked the live n8n workflow (`WF1 — Drive Statement → GitHub Parse`, id `NIwD3iarrxwH36qj`)
directly via the n8n API. It was **inactive**, had **zero execution history**, and still
contained the old rejected **Option A** node graph (base64-encodes the PDF, commits it into
`statements/` via GitHub's Contents API) — not the Option B redesign the 2026-07-08 note claims
was "manually imported." The manual import apparently didn't take, or was reverted.

**Fix**: had the user re-import the correct local `WF1 — Drive Statement → GitHub Parse.json`
(Option B: Drive Trigger → sends only `file_id`+`filename` to GitHub → Telegram Notify) via
n8n's Import from File, reattach the 3 credentials (krimRakOraDrive, krimRakOraGit,
krimRakOraBot), explicitly rebind the watched Drive folder to
`1enRhFKT8-0jT_JHbzA1i5DzJwDTbGlgs`, and activate it.

### Finding 2: GitHub `client_payload` bug
First live test: GitHub rejected the dispatch with `422 client_payload... is not an object`.
Root cause: the `Trigger GitHub Parse` HTTP Request node used "Using Fields Below" body mode,
which serializes an expression-interpolated value as a **string**, not a nested object — GitHub's
`repository_dispatch` API requires `client_payload` to be real JSON. **Fixed** by switching the
node to raw JSON body mode with an explicit nested object:
```json
{
  "event_type": "parse-statement",
  "client_payload": { "file_id": "{{ $json.id }}", "filename": "{{ $json.name }}" }
}
```
After this fix: Drive trigger fires, Telegram "received" notification fires, GitHub accepts the
dispatch. Remaining failures were entirely downstream, in GitHub Actions / `finance.py`.

### Finding 3: ~2 months of work were never pushed (the big one)
`git status`/`git log` on the user's real machine revealed the local working tree had **all of
Phase 1.5 through Phase 4**, the WF1 redesign, and `.claude/skills/` — none of it committed past
`ccc7de3` (June 3), and `origin/main` was still at `d5ef1ee9`. This is why GitHub Actions kept
running the *old* `parse-statement.yml` (no download step, wrong CLI flag) — the fixed version
only ever existed locally. **This was the actual root cause of the `FileNotFoundError:
statements/...` failures**, not a workflow logic bug.

Fixed by staging an explicit, curated file list (via a `.sh` script, see zsh note below) —
deliberately excluding secrets, `.omc/` (claude-mem's local session-memory cache, may contain
fragments of past conversations — must never be committed), and two unrelated stray files that
had ended up in the repo root (`life-path-decoder-review.html`, `life-path-decoder.skill` — a
different, unrelated project, moved out) — then committing and pushing as
**`32509b6857e5b0e58b8e76b0166016130595c89f`**. Also added `.omc/` and
`.claude/settings.local.json` to `.gitignore` (machine-local files that shouldn't be shared).

**Lesson for future sessions**: after any local-only stretch of work, check `git status` /
`git log origin/main..HEAD` early and often — don't assume "it's on GitHub" without checking.

### Finding 4: CI silently reported false success
Two stacking bugs, both now fixed in code:
1. `.github/workflows/parse-statement.yml`'s "Write .env" step never wrote a `CARD_PASSWORDS`
   line at all — so `finance.py parse --pdf` always failed with `✗ CARD_PASSWORDS not set in
   .env` in CI even though it's set correctly locally. Fixed by adding
   `echo "CARD_PASSWORDS=${{ secrets.CARD_PASSWORDS }}" >> .env` to that step.
2. **Systemic bug in `finance.py`**: every error branch did `click.echo("✗ ...")` then a bare
   `return` — which exits 0 in Click/Python. GitHub Actions' `if: success()` / `if: failure()`
   step conditions trust the process exit code, so a *failed* parse was still reported as
   `if: success()` and sent a false "✅ Statement parsed and written to Sheets." Telegram message.
   Fixed by changing every error branch in `decrypt` and `parse` (both commands) to
   `raise SystemExit(1)` after the `click.echo("✗ ...")` — confirmed the legitimate non-error
   `return`s (dry-run, "no active debts") were left untouched, per Surgical Changes.

**⚠️ Not yet confirmed as of session close**:
- Whether the commit containing these two fixes was actually pushed — the last GitHub Actions
  run seen still checked out the pre-fix commit `32509b6`. User confirmed via `git status` that
  both `finance.py` and `.github/workflows/parse-statement.yml` were staged
  ("Changes to be committed"), and was given commit+push commands, but the resulting commit hash
  was never reported back.
- Whether the `CARD_PASSWORDS` secret actually exists in the GitHub repo's Actions secrets (the
  `.env`-writing fix is useless if the secret itself was never added — user was asked to check,
  not yet confirmed).
- A genuinely successful, real end-to-end WF1 run (Drive upload → Telegram "received" → GH
  Actions download+decrypt+parse → real new row in the Transactions sheet → Telegram "✅ parsed"
  that is actually true) **has not yet been observed**. Every run so far either 422'd, 404'd
  (see below), or false-succeeded.

### Known minor issue (not fixed, low priority)
The "Archive source file in Google Drive" step 404s — it posts to `N8N_ARCHIVE_WEBHOOK_URL`,
whose target n8n workflow is inactive. Cosmetic: the statement still gets parsed and written to
Sheets correctly; only the "move source PDF to Archive folder" cleanup step fails. Fix later by
activating (or rebuilding) that archive workflow — not urgent.

### Tooling friction notes (for future sessions)
- **iCloud cloud-placeholder files**: this project folder is under `~/Documents/...` with
  iCloud "Desktop & Documents Folders" sync on (see Environment note above). Multiple files hit
  "is a cloud placeholder (not downloaded)" errors when staging from the device this session.
  Fix: user runs `brctl download .` (whole project, faster than file-by-file) + a short wait,
  verifies with `cat <file> | wc -c`, then retry.
- **zsh vs bash paste**: zsh's `interactive_comments` is off by default — pasting a multi-line
  script with `#` comments directly into an interactive zsh Terminal breaks it
  (`zsh: command not found: #`), especially with `\` line continuations. Fix: deliver an actual
  `.sh` file and have the user run `bash script.sh` instead of pasting raw multi-line commands.
- `.github/workflows/*` files **cannot** be written back via the device-bridge `device_commit_files`
  tool ("protected file") — the user has to make those edits manually (`open -e <path>`).

### Next session — resume here
**Keyword: `WF1-verify`**

Say "WF1-verify" (or paste this section) to a new session on this project and have it, in order:
1. Run `git log -3` and `git status` on the real repo to confirm the `finance.py` +
   `parse-statement.yml` fix commit actually landed on `origin/main`.
2. Confirm the `CARD_PASSWORDS` secret exists in the GitHub repo's Settings → Secrets and
   variables → Actions (ask the user to check, or check via `gh secret list` if the `gh` CLI is
   authenticated).
3. Do one real test drop: upload a real (or test) statement PDF to the watched Drive folder and
   watch it through: Telegram "received" → GitHub Actions run (should show the download step
   succeed, `CARD_PASSWORDS` present, parse succeed) → a real new row in the Transactions sheet →
   Telegram "✅ parsed" that is actually true this time.
4. Only once that's a clean pass, mark Phase 2/WF1 ✅ Done in the status table above and move to
   WF3 (daily FX sync) per the council's ordering.

---

## Session: 2026-08-02 — WF1 verified end-to-end (finally)

Ran the `WF1-verify` checklist from the note above. Every one of the four steps turned up a new,
real bug — none of the ones this file previously claimed were the blockers. Full chain, in order:

### Step 1 — fix commit confirmed pushed
`git log`/`git status` on the real repo confirmed commit `3405786` (the exit-code + CARD_PASSWORDS
CI fixes from 2026-08-01) landed on `origin/main` — verified via the git reflog
(`origin/main@{...} update by push`, not just a stale fetch). This part actually held.

### Step 2 — CARD_PASSWORDS secret
User confirmed it exists in GitHub Settings → Secrets → Actions. (No `gh` CLI on this machine to
verify independently — took the user's word for it, and step 3 later proved it was in fact set.)

### Finding A — there were TWO n8n workflows both named "WF1 — Drive Statement → GitHub Parse"
Pulling `NIwD3iarrxwH36qj` (the id this file has referenced since June) via the n8n API showed it
**still inactive, zero executions, still Option A** — exactly the broken state the 2026-08-01
session's "Finding 1" claimed to have already fixed. The reimport never actually saved. Turned out
the user had been editing a **different, second workflow** the whole time:
**`yO2jvG2di7fSeAz0`** (created 2026-07-07) — correct Option B design, using credentials named
"KrimRak Aura" / "KrimRak Internal Secret" / "telegram_lifeos_bot" (borrowed-looking names from the
unrelated astrology-decoder project sharing the same n8n "KRIMRAK" team) instead of the
`krimRakOra*`-named ones this file documents. Confirmed those credentials are actually valid and
correctly scoped — the real bot on the user's phone, real access to the right Drive folder — so no
functional problem, just a naming/documentation mismatch.

**`yO2jvG2di7fSeAz0` is now the correct id for WF1 going forward. `NIwD3iarrxwH36qj` is dead —
inactive, zero executions, still Option A — and should be deleted next time someone's in the n8n
UI, to stop this exact confusion from happening a third time.** Not deleted this session (didn't
want to take a destructive action without the user driving it).

**Lesson**: `mcp__n8n__update_workflow` still hits the same `settings must NOT have additional
properties` connector bug reported 2026-08-01 (tried again, confirmed still broken) — any n8n
workflow change has to go through the UI, and **must be re-verified via `get_workflow` after**,
not trusted from the user saying "done"/"published." This happened twice this session (see Finding
B) before it actually landed.

### Finding B — `.github/workflows/parse-statement.yml` had a literal tab character breaking the whole file
First real test drop: Drive trigger fired, GitHub dispatch succeeded (clean 204), Telegram "received"
fired — but **no GitHub Actions run ever appeared**. No error anywhere; `repository_dispatch`
simply has nothing to associate the event with if the workflow YAML doesn't parse, so it fails
completely silently. Root cause: the 2026-08-01 CARD_PASSWORDS fix (Finding 4 in that session) had
introduced a **literal tab character** on that line instead of spaces — confirmed with
`yaml.safe_load` (`found character '\t' that cannot start any token`). This had been silently
broken since the fix commit was pushed; nobody had actually gotten a workflow run to fire since
then to notice.

Fixed once locally and pushed — except origin/main had **also** picked up two intermediate
commits ("Update parse-statement.yml" ×2, GitHub's auto-message for web-UI edits) that the user
had made trying to fix the same tab in the GitHub web editor. Those attempts made it *worse* — the
browser editor inserted literal tabs on all 6 lines instead of the original 1. Had to
`git reset --hard origin/main` and refix from that actual current state (not the stale local
parent), replacing the exact `\t\t  ` prefix with proper spaces, re-validating with
`yaml.safe_load` before committing this time. **Lesson: don't fix YAML indentation via GitHub's
web editor in this repo — it inserts real tabs. Edit locally and push instead.**

### Finding C — service account had zero access to the Google Sheet
With the YAML fixed, GH Actions finally ran for real: checkout → download → decrypt → parse all
succeeded, but the Sheets write failed with `gspread.exceptions.APIError: [403]: The caller does
not have permission`. Checked the sheet's sharing settings directly — only `rakaisa@gmail.com`
(owner) had access; `krimrakora@krimrakora.iam.gserviceaccount.com` (the service account in
`credentials.json`, used by both `sheets.py` and CI) had **never been shared on this sheet at
all**, despite Phase 0 supposedly having set this up back in May. User added it as Editor via the
Sheets UI — confirmed via screenshot (the `get_file_permissions` API call kept not showing the
grant even after the user added it and wanted twice; trust the actual Sheets UI over that specific
tool call in this environment, it appears to be unreliable/cached here).

One unrelated thing noticed in that screenshot, flagged but not changed: **General access on the
sheet is "Anyone with the link — Editor"** — anyone who gets the link can edit this financial
data, not just view it. Worth tightening to "Restricted" at some point; user's call.

Good news buried in the same failed run: the `if: failure()` Telegram step fired a truthful
"❌ Statement parse failed" message (not a false "✅") — confirms the 2026-08-01 exit-code-honesty
fix (Finding 4 there) is genuinely working now.

### Step 3 — clean end-to-end pass, confirmed twice independently
With the Sheets permission fixed, re-dropped the same test PDF
(`4315XXXXXXXX4018_347625_Retail_Amazon_NORM.pdf`, a real ICICI Amazon Pay statement) into the
watched Drive folder. Full chain: Telegram "received" → GitHub Actions run → download → decrypt →
parse (`✓ 60 rows written, 0 duplicates skipped`, 20 flagged for category review at <80%
confidence — expected categorizer behavior, not an error) → Telegram "✅ Statement parsed and
written to Sheets." (genuinely true this time) → independently re-read the Transactions tab via a
separate tool call and confirmed the 60 real rows are actually there (real merchants, dates,
amounts, categories, budget_type all populated).

**Known pre-existing minor issue, unchanged**: the "Archive source file in Google Drive" step
still 404s (`N8N_ARCHIVE_WEBHOOK_URL` target workflow inactive) — cosmetic, doesn't block parsing,
same as noted 2026-08-01.

### Step 4 — status table updated
Phase 2/WF1 marked ✅ Done above. Per the council's ordering from 2026-08-01, next up is **WF3
(daily FX sync)** — `FX_Rates` tab currently only has data through 2026-07-08, consistent with WF3
never having run.

### Loose ends for next session
- Delete the dead `NIwD3iarrxwH36qj` workflow in n8n (superseded by `yO2jvG2di7fSeAz0`) to stop
  the duplicate-name confusion from recurring.
- Consider renaming `yO2jvG2di7fSeAz0`'s credentials from the borrowed `KrimRak Aura` /
  `KrimRak Internal Secret` / `telegram_lifeos_bot` names to the project's own `krimRakOra*`
  naming convention, purely for clarity — they work fine as-is, this is cosmetic.
- Tighten the Transactions sheet's general access off "Anyone with the link — Editor" if the user
  wants that (flagged, not acted on).
- `docs/WIKI.md` (updated this session to match — Phase 2 status, architecture diagram, current
  state) and `krimrakora-docs-commit.sh` (pre-existing docs-commit helper, not authored this
  session) were both untracked going into this session; committed together with `CLAUDE.md` at
  session close.
- WF2 (Telegram agent) still not started — after WF3/WF4/WF5 per the existing ordering.

### Next session — resume here
**Keyword: `WF3-build`**

Say "WF3-build" (or paste this section) to a new session on this project and have it, in order:
1. Read the `n8n-wf3-fx-sync` skill for the workflow runbook, and `scripts/sync_fx.py` for what
   the local CLI equivalent already does (WF3 is just that on a daily n8n cron, per the
   `## n8n Workflows (Phase 2+)` table above: `30 0 * * *` / 6am IST).
2. Build/import the WF3 n8n workflow watching the same `git status` / `get_workflow`-verify
   discipline this session had to learn the hard way: don't trust a UI "done" — pull the workflow
   back via the n8n API after any change and confirm it actually saved.
3. Do one real test run and confirm `FX_Rates` gets a new row for today's date before marking it
   done.
4. While in n8n: delete the dead `NIwD3iarrxwH36qj` workflow (see `## Session: 2026-08-02`) if not
   already done.
5. Update the status table and this file's session log the same way this session did, then move
   to WF4 (daily spend summary) per the existing ordering.
