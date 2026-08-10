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
| Phase 3 — n8n WF3+WF4+WF5+WF6 | ✅ All 4 done 2026-08-10 | WF3 (daily FX sync) built, verified, active — id `ArQY0BWqFYQLTRVA`. WF4 (daily spend summary) built, verified, active — id `LpmXgr7n8UQNjJ5T`. WF5 (monthly report) built, verified, active — id `BxYQfsOgCooNMeri`, see `## Session: 2026-08-09 — WF5 built & verified`. WF6 (error handler) built, verified, active — id `YeWq5wH7cTboCQrL`, registered as Error Workflow on WF1/WF3/WF4/WF5, see `## Session: 2026-08-10 — WF6 built & verified, Kotak parse bug fixed` |
| Phase 4 — Debt + Net Worth | ✅ Done | `debt_planner.py`, `net_worth.py`, `report.py` written + wired |
| Phase 5 — Hardening | ✅ Done, red-teamed 2026-08-10 | 93/93 tests pass; test_sheets flake fixed (see below); categorizer.py hardened against prompt injection + gray-area confidence calibration; WF1 Telegram messages now surface real parse results. Open: GitHub repo is public (top risk, unfixed — user's call), Transactions sheet still link-editable. See `## Session: 2026-08-10 (cont.) — Red team review` |
| Phase 6 — n8n WF2 | ✅ Built & verified end-to-end 2026-08-10 | Telegram AI Agent, id `ZwoPsgjdauO1atzi`, active, registered WF6 as Error Workflow. ADD_EXPENSE, QUERY_BUDGET (this-month and named-month), and UNKNOWN all verified against real Telegram messages + independent sheet re-reads. **All 6 planned n8n workflows (WF1–WF6) are now built, verified, and active — Phase 2+ is complete.** See `## Session: 2026-08-10 (cont.) — WF2 built & verified` |
| Phase 7 — Review flow + Income parsing | ✅ Built & verified 2026-08-10 | Low-confidence categorizations now persist a `[review: confidence NN%]` tag in `notes` and are fixable via `scripts/review_transactions.py` (new rows only, not retroactive). `income_parser.py` extracts salary NEFT credits from Kotak savings-account statements into `Income`, routed ahead of card detection in `finance.py parse --pdf` — fixes a real false-success bug where a savings statement silently produced "0 rows written" (misdetected as the Kotak credit card). Verified against 4 real months, live-written for July. `Debts`/`Goals`/`Net_Worth`/`Vendor_Map` still unused. See `## Session: 2026-08-10 (cont.) — review-correction flow + Income parsing` |
| Phase 8 — Kotak savings full ledger | ✅ Built & verified 2026-08-10 | `savings_ledger.py` classifies every line of a Kotak savings statement (not just salary) into salary/SIP/CRED Club/family-transfer/personal-spend/loan buckets, derives each row's signed amount from consecutive printed-balance deltas (handles pdftotext losing the Dr/Cr column split), and writes SIPs (deterministic `Investment/SIP/save`), CRED Club + family transfers (`[review: ...]` tagged, ambiguous purpose), and personal spend (through the real Claude categorizer) into `Transactions` under `card_account = "Kotak Savings"`. Gold-loan-linked lines ("Ins Debit"/"Pyt Loan", GLN-tagged) are deliberately reported only, never written — real loan terms need the user, not one month's cash flow. Live-verified for July: 48 rows written, 42 flagged for review, independently re-summed to ₹135,966.76. All 42 subsequently reviewed and categorized (see `## Session: 2026-08-10 (cont.) — reviewed all 48 Kotak Savings rows`). `Debts` still has zero real rows — the found gold loan is the next real candidate once the user supplies its terms. See `## Session: 2026-08-10 (cont.) — Kotak savings full ledger` |

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
`Income` (has real data as of 2026-08-10, see `income_parser.py`) · `Transactions` (now includes
`card_account = "Kotak Savings"` rows via `savings_ledger.py`, not just the 5 credit cards) ·
`Debts` (unused — a real gold loan was found in the Kotak savings statement 2026-08-10, needs the
user's actual loan terms to enter) · `Budget` · `Goals` (unused) · `Net_Worth` (unused) ·
`FX_Rates` · `Categories` (57 rows seeded) · `Vendor_Map` (unused)

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
| `sheets.py` | `get_sheet()`, `append_rows()`, `read_all()`, `update_row()` |
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
| `scripts/review_transactions.py` | Interactive CLI to fix low-confidence categorizations flagged `[review: confidence NN%]` in `notes` |
| `income_parser.py` | Detects a Kotak savings-account statement (`is_kotak_savings_statement()`), extracts salary NEFT credits (`extract_kotak_savings_income()`) into `Income`. Routed ahead of card detection in `finance.py parse --pdf` |
| `savings_ledger.py` | Full Kotak savings-statement ledger: `classify_savings_transactions()` buckets every line (salary/sip/cred_club/family/spend/loan) with signed amounts from balance deltas; `extract_merchant()` pulls a name out of a `UPI/...` description. Feeds `finance.py`'s `_parse_kotak_savings_full()` |

---

## CLI commands (all working)
```bash
python finance.py parse --file statements/ICICI_Bank.md
python finance.py parse --file statements/ICICI_Bank.md --dry-run
python finance.py parse --pdf dump/icici/statement.pdf          # Module 4 — decrypt+extract+parse in one step
python finance.py parse --pdf dump/kotak/statement.pdf --dry-run
python finance.py parse --pdf dump/kotak/savings_statement.pdf  # Kotak savings statement → Income (salary credits only)
python finance.py debt                          # avalanche plan
python finance.py debt --extra 5000             # with extra monthly payment
python finance.py worth                         # net worth snapshot (interactive)
python finance.py report --month 2026-05 --dry-run
python finance.py report --month 2026-05        # + uploads to Drive
python finance.py decrypt --file dump/icici/statement.pdf   # Module 1 — outputs *_decrypted.pdf

python3 scripts/setup_sheets.py                 # idempotent sheet setup
python3 scripts/sync_fx.py                      # FX sync
python3 scripts/query_budget.py --month 2026-06
python3 scripts/review_transactions.py           # fix low-confidence categorizations
python3 scripts/quick_add.py --merchant "Zomato" --amount 350
```

---

## n8n Workflows (Phase 2+)
- **WF1** Drive → GH Actions `parse-statement` → `finance.py parse` → Sheets
- **WF2** Telegram AI Agent (Claude haiku, quick-add, budget queries) — ✅ built & verified 2026-08-10, id `ZwoPsgjdauO1atzi`, active, in KRIMRAK project
- **WF3** Daily FX sync 6am IST (cron `30 0 * * *`) — ✅ built & verified 2026-08-02, id `ArQY0BWqFYQLTRVA`, active, in KRIMRAK project
- **WF4** Daily spend summary 9pm IST (cron `30 15 * * *`) — ✅ built & verified 2026-08-09, id `LpmXgr7n8UQNjJ5T`, active, in KRIMRAK project
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
python -m pytest tests/ -q   # 106 tests total, all passing (as of 2026-08-10)
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
- `tests/test_categorizer.py` — 6 tests ✅ (prompt-injection filter, added 2026-08-10)
- `tests/test_income_parser.py` — 5 tests ✅ (Kotak savings-statement income extraction, real July fixture, added 2026-08-10)
- `tests/test_savings_ledger.py` — 8 tests ✅ (full Kotak savings-statement ledger classification, real July fixture — all 53 real transactions, contiguous, added 2026-08-10)
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
> **Superseded 2026-08-02** — WF3-build is done, see
> `## Session: 2026-08-02 — WF3 built & verified` below for what actually happened. Left below,
> per this project's own "mention, don't delete" Surgical Changes rule.

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

---

## Session: 2026-08-02 (cont.) — WF3 built & verified

Ran the `WF3-build` checklist from the note above, same session day.

### Dead workflow status
`NIwD3iarrxwH36qj` was already `isArchived: true` when checked via `get_workflow` — someone (or
n8n itself) had archived it since the last session. Archived is not the same as hard-deleted, but
it no longer shows in the default workflow list, which was the actual problem (duplicate-name
confusion). Left archived rather than hard-deleting — user can delete it for real if they want,
not done without them driving it (same reasoning as last session).

### Built WF3, learned `create_workflow` works where `update_workflow` doesn't
Built the 8-node workflow from the skill runbook (Schedule Trigger `30 0 * * *` → HTTP GET FX API
→ Code: parse/compute 8 currencies → Sheets Append, with an error branch: Sheets Read last rates →
Code: carry forward → Sheets Append + Telegram alert). `mcp__n8n__create_workflow` (a different
API endpoint than `update_workflow`) worked cleanly — the workflow saved correctly on the first
try, confirmed via an immediate `get_workflow` re-fetch. **`update_workflow` is still broken**
(hit the exact same `settings must NOT have additional properties` error reported 2026-08-01 and
reconfirmed 2026-08-02 — third time now) — any *edit* to an existing workflow still has to go
through the n8n UI; only brand-new workflow creation works via the API. Used `$vars.FX_API_KEY`
(not `$env`, per the standing n8n Cloud rule) for the API key, deliberately not hardcoded like
WF1's Drive folder ID — it's a real secret and this JSON is git-committed.

`create_workflow` has no project parameter — the new workflow landed in the user's **personal**
n8n project by default, not the KRIMRAK team project WF1/WF2 live in. User moved it manually in
the UI; confirmed via `get_workflow` afterward (`projectId` now `4KP0kUrAplXZ3AZN` / "KRIMRAK").

User also completed the two other manual setup steps this required — added an n8n Variable
`FX_API_KEY` and attached a `google_lifeos` Google Sheets OAuth2 credential to both Sheets nodes
— both independently re-verified via `get_workflow`, not taken on trust.

### Real bug found: `appendOrUpdate` silently corrupted data
First test run "succeeded" (green execution, no errors) but independently re-reading the
`FX_Rates` sheet (not just trusting the execution status — same lesson as WF1's false-success
finding from 2026-08-01) showed today's 8 rows were wrong: **USD was missing entirely and JPY was
duplicated** (`JPY, GBP, EUR, SGD, AED, THB, MYR, JPY` instead of the expected 8 distinct
currencies). Root cause: the Sheets Append node's `appendOrUpdate` operation was configured with a
two-column match (`date` + `currency_code`, per the skill doc), but in practice it behaved like a
**date-only** match — since all 8 items in a batch share the same `date`, each subsequent
currency's write matched and overwrote the row from the previous currency instead of inserting its
own. A second test run (before the bug was caught) compounded it further.

**Fix**: switched the node from `appendOrUpdate` to plain `append`. Upsert semantics weren't
actually needed here — a given `(date, currency_code)` pair is only ever written once per real run
(the daily 6am cron); `appendOrUpdate` was solving a problem that doesn't really exist in
production use. Trade-off, flagged in the workflow's sticky note: manually re-running the workflow
more than once on the same day will now create duplicate rows for that day (acceptable — dedupe
manually if it happens, same category of issue as the local `sync_fx.py` CLI already has its own
`already_synced` guard for the same reason).

Tried pushing this one-field fix via `update_workflow` first — hit the same broken-`update_workflow`
error again. User made the fix manually in the n8n UI (Sheets Append node → Operation → Append,
cleared the match-on columns) and saved — which also activated the workflow (`active: true`) as a
side effect, which is actually the desired end state (daily cron now live).

### Clean verification
Re-read the `FX_Rates` sheet independently after the fix: exactly 8 rows for 2026-08-02, one row
per currency (USD 95.511, GBP 128.4027, EUR 109.7695, SGD 74.3494, AED 26.001, THB 2.8555, MYR
23.3699, JPY 0.5995), no duplicates, nothing missing.

**Not yet tested**: the error branch (Sheets Read last rates → carry-forward → Telegram alert) —
no API failure was exercised this session. Also, per the skill runbook, the Telegram alert's error
output is meant to eventually call WF6 (error handler) — WF6 doesn't exist yet (Phase 3, WF4/WF5
next per ordering, WF6 after that), so that edge stays unwired for now.

### Loose ends for next session
- WF3's error/fallback branch is unexercised — worth a deliberate bad-API-key test at some point,
  not blocking since the happy path (the actual daily job) is verified.
- `NIwD3iarrxwH36qj` still exists in archived state, not hard-deleted — user's call whenever they
  want it gone for good.
- WF4 (daily spend summary, 9pm IST) is next per the existing ordering.

### Next session — resume here
> **Superseded 2026-08-09** — WF4-build is done, see
> `## Session: 2026-08-09 — WF4 built & verified` below for what actually happened. Left below,
> per this project's own "mention, don't delete" Surgical Changes rule.

**Keyword: `WF4-build`**

Say "WF4-build" (or paste this section) to a new session on this project and have it, in order:
1. Read the `n8n-wf4-daily-summary` skill for the workflow runbook.
2. Build the WF4 n8n workflow using `create_workflow` (not `update_workflow` — confirmed broken a
   third time this session) for the initial build, then hand any post-creation edits to the user
   via the n8n UI, re-verifying every change with `get_workflow` afterward — never trust a UI
   "done" on its own.
3. Watch for the same class of bug WF3 had: independently re-read whatever sheet/tab the workflow
   writes to after a test run — don't trust a green execution status alone, verify the actual data.
4. Do one real test run, confirm the output is correct, then update the status table and this
   file's session log the same way this session did, and move to WF5 (monthly report) per the
   existing ordering.

---

## Session: 2026-08-09 — WF4 built & verified

Ran the `WF4-build` checklist from the note above, plus an `llm-council` pass before build (user
explicitly asked for the council first) and used oh-my-claudecode's n8n MCP tools for the actual
build. Full chain, in order:

### Council caught a real schema bug before any code was written
Convened the 5-advisor council on "should we proceed with WF4 now, following the same process as
WF3." All five converged: yes, but fix a bug first. Comparing the `n8n-wf4-daily-summary` skill
runbook's Code node against CLAUDE.md's own schema table (`## Transaction schema` /
`## Budget split`) turned up a real mismatch nobody had caught: the skill's Code node aggregated
spend using budget_type keys `needs`/`wants`/`savings` (plural) — but the actual Transactions
sheet stores `need`/`want`/`save`/`debt`/`petty` (singular, `save` not `savings`). Unfixed, three
of five categories would have silently read ₹0 every night, forever, with a green execution and no
error — the same failure shape as WF3's `appendOrUpdate` bug from 2026-08-02, except worse because
it would land directly in the user's face every night instead of in a rarely-checked FX_Rates tab.
Fixed the skill runbook's Code node (`.claude/skills/n8n-wf4-daily-summary.md`) before touching
n8n, and added a self-check the council also suggested: sum the mapped buckets and compare against
the raw total, warning via Telegram if an unmapped budget_type value ever shows up (catches the
*next* schema drift automatically instead of relying on a human noticing months later).

### Build: `create_workflow` worked cleanly again
Same pattern as WF3 — `create_workflow` (not `update_workflow`) built the whole 7-node graph
(Setup Notes sticky, Cron Trigger, Sheets Read: Transactions, Sheets Read: Budget, Code: Aggregate
& Flag, If: Has Transactions?, two Telegram nodes) in one call, confirmed via immediate
`get_workflow` re-fetch. Landed in the user's personal project again (same as WF3's first attempt)
— user moved it to KRIMRAK manually, re-verified via `get_workflow` after. User also attached
`google_lifeos` (Sheets OAuth2) and `telegram_lifeos_bot` (Telegram) credentials manually and
activated it — each step re-verified via `get_workflow`, not taken on trust. User asked why
"lifeos"-named credentials were being used on a KrimRak workflow — same answer as WF1/WF3's
2026-08-02 finding: cosmetic naming leftover from an unrelated project sharing this n8n account,
credentials themselves are correct and already proven to work. Not renamed (still on the loose-end
list from 2026-08-02, still not urgent).

### Real bug 1 — parallel fan-in race condition
First test run threw `ExpressionError: Node 'Sheets Read: Budget' hasn't been executed` inside the
Code node. Root cause: both Sheets Read nodes originally fanned into the Code node's same input in
parallel (mirroring how a Code node references other nodes by name via `$('NodeName')`) — but in
n8n, a node with multiple incoming connections fires as soon as the FIRST predecessor completes,
it does not wait for all of them. Fixed by chaining the two Sheets Read nodes sequentially
(Trigger → Budget → Transactions → Code) instead of fanning in parallel. This is a new lesson for
this project's n8n-wiring notes, distinct from anything WF1/WF3 hit.

### Real bug 2 — empty Budget sheet silently killed the whole run
User asked "shouldn't we set a budget in the Budget sheet?" — turned out the sheet had zero rows,
and n8n's default behavior is to halt the entire workflow when a node produces zero output items.
With Budget wired before Transactions in the new sequential chain, an empty Budget sheet meant
**no Telegram message at all**, not even for real spend that happened — the budget-warning feature
being unconfigured shouldn't have been able to silence the core "did I spend money today" signal.
Fixed by setting `alwaysOutputData: true` on both Sheets Read nodes so an empty result doesn't
halt downstream execution. User then populated the Budget sheet for 2026-08 using CLAUDE.md's
40/30/20/10 need/debt/save/want split on a stated ₹183,000/month income (need 73200, debt 54900,
save 36600, want 18300; petty left to the user's own habits per CLAUDE.md's "tracked separately"
note).

### Real bug 3 — the 5x-inflation bug, found via a genuinely confusing symptom
Test run after populating Budget showed `total: 2500, needs: 2500, txn_count: 5` for a single real
₹500 test transaction. User asked directly why. First hypothesis (duplicate rows in the sheet) was
wrong — user confirmed only one row existed for that date. Second hypothesis (n8n UI showing
accumulated output from repeated manual node-execute clicks) was also wrong — a clean single "Test
workflow" run still showed 5x. The actual root cause, found by counting: 5 exactly matches the
number of Budget rows just added (need/want/debt/save/petty). In n8n, a node downstream of another
node that outputs multiple items re-executes once *per incoming item* by default — so "Sheets
Read: Transactions," chained directly after "Sheets Read: Budget" (which now output 5 items),
re-ran its full sheet read 5 times, and `$('Sheets Read: Transactions').all()` in the Code node
collected all 5 runs' worth of rows, inflating every total by exactly 5x. This was a bug introduced
by this session's own Bug 1 fix (the sequential chaining), not something inherent to the original
design — fixed by setting `executeOnce: true` on the Transactions node so it runs exactly once
regardless of how many Budget rows exist. Cross-checked via `list_executions` / `get_execution`
against the actual n8n execution record rather than trusting the UI node-output panel alone, since
the panel had already produced one red herring (the accumulated-clicks theory) earlier in the same
debugging pass.

### Clean verification, both branches
Final test run: `txn_count: 1, total: 500, needs: 500` for the one real Blinkit test row — matched
by hand. Telegram message confirmed correct. Deleted the test row, re-triggered: `has_transactions:
false`, Telegram sent "✓ No spending logged today" — both branches of the `If: Has Transactions?`
switch verified against real data, not just a green execution.

### Loose ends for next session
- WF4's weekly-budget-warning branch (the `pct >= 80` logic) is unexercised — both test runs stayed
  well under any weekly threshold. Worth a deliberate over-budget test at some point, not blocking
  since the core spend-reporting path (the actual daily job) is verified.
- Same `NIwD3iarrxwH36qj` / general-access-sheet loose ends from 2026-08-02 remain untouched.
- `petty` has no Budget row yet (user chose to leave it per CLAUDE.md's "tracked separately" note)
  — fine as-is, the Code node already handles a missing budget row for any type gracefully.
- WF5 (monthly report) is next per the existing ordering.

### Next session — resume here
**Keyword: `WF5-build`**

Say "WF5-build" (or paste this section) to a new session on this project and have it, in order:
1. Read the `n8n-wf5-monthly-report` skill for the workflow runbook, and diff it against
   CLAUDE.md's schema tables (`## Transaction schema`, `## Budget split`) *before* building —
   the WF4 session found a real singular/plural budget_type mismatch this way; check whether WF5's
   runbook has the same class of bug before writing any node.
2. Build using `create_workflow` for the initial build (not `update_workflow` — though note WF4's
   session found `update_workflow` actually worked for connections/node-property-only edits after
   creation; still don't rely on it for a first build), then hand credential/project-move steps to
   the user via the n8n UI, re-verifying every change with `get_workflow` afterward.
3. If any node is chained downstream of another node that can output more than one item, check
   whether it needs `executeOnce: true` — WF4 hit a real 5x-inflation bug from this exact pattern
   when a downstream Sheets Read re-executed once per incoming item. Also set `alwaysOutputData:
   true` on any Sheets Read whose result feeds a decision that shouldn't be silently skipped if the
   sheet is empty.
4. Do a real test run and cross-check via `list_executions`/`get_execution`, not just the UI node
   panel (it can show misleading accumulated data). Verify by hand-summing real data, not just a
   green execution or a plausible-looking message.
5. Update the status table and this file's session log the same way this session did.

---

## Session: 2026-08-09 — WF5 built & verified

Ran the `WF5-build` checklist from the note above, using an `llm-council` pass (5 advisors +
chairman synthesis) before writing any code, plus the oh-my-claudecode n8n MCP tools for the
build. Full chain, in order.

### Council-independent pre-build audit caught 4 real schema mismatches
Before convening the council, diffed the `n8n-wf5-monthly-report.md` runbook's Code node
against `scripts/setup_sheets.py` (source of truth) field-by-field. Found four mismatches, all
of the same class as WF4's `needs/wants/savings` bug — the runbook was hand-written against a
plausible-sounding schema that didn't match reality:
- Debts: runbook used `account_name`/`balance_inr`/`original_inr` → actual columns are
  `debt_name`/`total_outstanding`/`initial_amount`.
- Net_Worth: runbook used `net_worth_inr` and sorted rows by `date` → actual column is
  `net_worth`, and there is no `date` column at all on this sheet, only `month`. This one is
  structural, not a rename — the sort logic itself needed rewriting.
- Goals: runbook used `saved_inr` → actual column is `saved_so_far`.
- Income: runbook filtered `r.month === reportMonth` → Income has no `month` column, only
  `date`; fixed to `r.date.startsWith(reportMonth)`.

Ran the council on "should we proceed now, and what else to check" with this finding already in
hand. All five advisors converged on proceed, with one added catch worth keeping: the Outsider
flagged that a partial diff finding 4 bugs can create false confidence it found *all* of them —
re-audited every field the Code node touches (not just the four that stood out) before writing
any node, confirmed no fifth mismatch existed.

### First wiring draft reproduced the exact bug it was trying to avoid
Initial redesign fanned all 5 Sheets Read nodes in parallel directly into `Code: Build Report`
with no Merge node, reasoning "nothing here is chained after a multi-item node, so WF4's race
can't happen." That reasoning was wrong and caught before build (by the Contrarian advisor,
independently re-derived by re-reading n8n's actual multi-input semantics): a node with multiple
incoming connections in n8n fires as soon as the FIRST predecessor completes, not after all of
them — that's what WF4 actually hit, and a 5-way parallel fan-in reproduces it regardless of
whether a Merge node sits downstream. Corrected to WF4's actual proven fix: sequential chaining
(Transactions → Income → Debts → Goals → Net_Worth → Code: Build Report), `alwaysOutputData:
true` on all 5 reads, `executeOnce: true` on every node downstream of a node that can emit more
than one item (Income/Debts/Goals/Net_Worth/Code: Build Report — not Transactions, whose only
parent always emits exactly one item).

### Build: `create_workflow` clean, landed in personal project again
`create_workflow` built the full 11-node graph (Setup Notes sticky, Cron Trigger, Code: Determine
Report Month, 5 sequential Sheets Reads, Code: Build Report, Convert to File, Drive Upload,
Telegram) in one call, confirmed via immediate `get_workflow` re-fetch — id `BxYQfsOgCooNMeri`.
Landed in the user's personal project again (same as WF3/WF4's first attempt) — user moved it to
KRIMRAK manually and activated it, re-verified via `get_workflow` after (`projectId`
`4KP0kUrAplXZ3AZN`, `active: true`). Reused WF3/WF4's exact credential IDs (`google_lifeos` for
all Sheets reads, `telegram_lifeos_bot` for the summary) and WF1's `KrimRak Aura` Google Drive
OAuth2 credential for the new Drive upload node — first workflow in this project to need Drive
write access outside WF1. User supplied the `reports/` Drive folder ID
(`1s3pAPWFbqdqgsIzrgiS8Ccjw439zXC-f`) since nothing in the repo had it recorded.

### Real bug found on the first test run: truthy-but-blank rows from empty sheets
Test run (against real July 2026 transaction data, no Debts/Goals/Net_Worth/Income rows yet)
"succeeded" — Telegram sent, Drive file created — but the report itself showed
`% paid off: NaN%` and `undefined: NaN%` under Goals. Root cause: `Sheets Read: Debts` and
`Sheets Read: Goals` returned a single blank-ish row from `getAll` on an all-header sheet, not a
genuinely empty array — so `debts.sort(...)[0]` and the Goals `.map()` picked up a *truthy* `{}`
object instead of `undefined`, defeating the `priorityDebt ? ... : 0` fallback the code already
had (that fallback assumed "no debt" meant an empty array, which held for `Net_Worth`'s simpler
`nwRows[0]?.net_worth || 0` pattern but not for the Debts/Goals logic, which branches on
truthiness of the whole row object). Fixed by filtering both reads to rows with a real
`debt_name`/`goal_name` before use — pushed via `update_workflow` (worked cleanly for this
node-content-only edit, consistent with WF4's finding that `update_workflow` is broken for
brand-new workflow creation but fine for editing an existing one), re-verified via `get_workflow`
immediately after.

### Clean verification
Re-triggered manually. Hand-checked the output against the raw Transactions data pulled via
`get_execution`: `need: ₹11949 + want: ₹54568 = ₹66517` (1 rupee off the reported `₹66516` due
to independent `toFixed(0)` rounding per category vs. the unrounded total — not a bug), matching
a manual sum of the 60 real July rows with `amount_inr > 0`. Telegram message and Drive file both
confirmed correct. Debts/Goals/Net_Worth/Income were genuinely empty this month (no real data
entered yet) and now render as `N/A`/`₹0`/no lines instead of `NaN` — the intended graceful
behavior once real Debts/Goals/Net_Worth data exists.

### Real bug 3 (2026-08-09, user-caught after the "verified" close above): amount_inr > 0 filter was wrong
The session above closed with a report showing `Total Spend: ₹66516` and called it verified —
hand-summed against the raw sheet data, which is exactly this project's standing rule, but the
hand-sum itself only checked that the code's positive-only filter matched its own output
consistently, not that the filter was the right thing to do. User caught it by independently
computing the expected net total (-32564.71) from the raw ledger and comparing against the
report's +66516 — they didn't match. Root cause: `Code: Build Report`'s Transactions filter
excluded `amount_inr <= 0` rows. Real statements contain charge/reversal/remainder triplets (a
purchase immediately reversed, then re-charged at the true net amount — same accounting pattern
CLAUDE.md already documents for Kotak/ICICI EMI conversions) — filtering to positives only
double-counted every reversed charge as real spend instead of netting it out. Fixed by removing
the `amount_inr > 0` filter entirely; verified by hand-summing ALL July `amount_inr` values
(positive and negative) to -32564.71, matching the user's independently-computed expectation.
Pushed via `update_workflow`, re-verified via `get_workflow`, re-tested: Telegram showed
`Spent: ₹-32565`, matching.

**Lesson, sharper than the existing "hand-verify, don't trust green execution" rule**: hand-
verifying a total by re-deriving it *from the code's own logic* isn't independent verification —
it just confirms the code is internally consistent, not that the logic is correct. Real
independent verification means computing the expected answer from first principles (what should
this number mean, given the domain) before looking at what the code produced, the way the user
did here. This session's first "verified" pass didn't do that.

**Side effect, resolved**: with net-inclusive totals, `Total Spend` can go negative in a month
with large debt-payment credits, which flipped `Net Saved = income - spend` positive even when
Income is ₹0 — mathematically correct but a confusing label. User asked for a different label;
renamed to `Net Cash Flow` in both the report markdown and the Telegram summary (accurate
regardless of sign, no math change).

### WF4 fixed with the same bug, same session
User asked to fix WF4 too, on the reasonable assumption that a sign-filter bug found in WF5's
Code node would exist wherever the same filter pattern was copied. Confirmed: WF4's
`Code: Aggregate & Flag` had the identical `parseFloat(t.amount_inr) > 0` filter. Removed it the
same way — sum ALL of today's Transactions rows regardless of sign. `has_transactions` was left
as "any row logged today" rather than "net spend nonzero" (a day with a full charge/reversal
pair netting to ₹0 still counts as a day something was logged) — a deliberate minimal choice, not
re-litigated with the user this session. Pushed via `update_workflow`, re-verified via
`get_workflow`. **Not yet re-tested against a real day with a charge/reversal pair** — WF4's own
daily cron will exercise it naturally, or it can be tested manually once a matching day exists in
Transactions.

### Final verification (2026-08-10) — real full-month data, all 4 cards
User loaded all real July statements (ICICI, SBI, RBL, Scapia) into the Transactions sheet via
WF1 (hit and resolved a Scapia password-rotation hiccup along the way — new password added to
the `CARD_PASSWORDS` GitHub Actions secret) and ran WF5 for real. First read: `Spent: ₹46061`,
user expected `-2309.39` and flagged it as wrong.

Hand-summed all July rows across all 4 cards independently from the raw sheet data: **+46061.03**
— exactly matching WF5's output. Confirmed no duplicate rows (user checked). Root cause of the
user's `-2309.39` figure: a manual click-and-drag row selection in the Sheets UI — this
Transactions sheet is **append-only by import batch per card, not sorted by date**, so each
card's July rows sit in a different, non-contiguous row range (ICICI ~61-168, SBI ~169-192, RBL
~193-228, Scapia ~230-280, each interleaved with that card's June rows). A manual selection
silently grabbed one card's block and missed the others. Had the user run a formula-based sum
(`SUMPRODUCT` keyed on `TEXT(date,"YYYY-MM")="2026-07"`) instead — returned `46061.03`, matching
WF5 exactly. **No code bug — WF5 is correctly verified against real, full production data.**

**Lesson for this project**: the Transactions sheet's append-by-batch layout (not sorted by
date) makes manual eyeballing/selection in the Sheets UI genuinely unreliable for cross-checking
totals — always use a formula (SUMIF/SUMPRODUCT keyed on the actual date column) instead, never
a manual row selection, when independently verifying a report's numbers against the sheet.

### Loose ends for next session
- WF5's Debts/Goals/Net_Worth/Income sections are still unexercised with real non-empty data —
  worth a deliberate test once the user populates those sheets, to confirm the Debt Avalanche and
  Goals Progress sections render correctly with real rows (not just gracefully with empty ones).
- WF4's sign-filter fix is unexercised against a real charge/reversal day — confirm correctness
  next time one occurs, the same way WF5's fix was confirmed against July's real data.
- WF6 (error handler) is next per the existing ordering — last workflow in the original Phase 2+
  plan. WF2 (Telegram agent) still not started, deliberately last per the council's 2026-08-01
  ordering.

### Next session — resume here
**Keyword: `WF6-build`**

Say "WF6-build" (or paste this section) to a new session on this project and have it, in order:
1. Read the `n8n-wf6-error-handler` skill for the workflow runbook.
2. Apply this project's now-standard pre-build discipline: diff the runbook's field/column
   references against `scripts/setup_sheets.py` (source of truth) before writing any node — WF4
   and WF5 both had real schema mismatches caught this way.
3. Build using `create_workflow` for the initial build, hand credential/project-move steps to the
   user via the n8n UI, re-verify every change with `get_workflow` — never trust a "done" without
   re-fetching.
4. Watch for the same wiring bugs this project keeps hitting: a node with multiple incoming
   connections fires on the FIRST predecessor, not all of them (use sequential chaining, not
   parallel fan-in); a node downstream of a multi-item node re-executes once per item unless
   `executeOnce: true`; an empty source sheet halts the workflow unless `alwaysOutputData: true`.
5. Do a real test run, verify by independently recomputing the expected result from first
   principles (not by re-deriving it from the code's own logic) before trusting any number.
6. Update the status table and this file's session log the same way this session did.
- Same `NIwD3iarrxwH36qj` (archived, not deleted) and general-access-sheet loose ends from
  2026-08-02 remain untouched.
- WF6 (error handler) is next per the existing ordering — last workflow in the original Phase 2+
  plan. WF2 (Telegram agent) still not started, deliberately last per the council's 2026-08-01
  ordering.

---

## Session: 2026-08-10 — WF6 built & verified, Kotak parse bug fixed

### Real bug: Kotak statement parse crashed CI with "header row is not unique"
Ran the `WF6-build` checklist, plus fixed a live production bug the user reported at session
start: a Kotak statement drop through WF1 failed `finance.py parse --pdf` in GitHub Actions with
`gspread.exceptions.GSpreadException: the header row in the worksheet is not unique`. Root cause:
`sheets.py read_all()` calls gspread's `get_all_records()`, which pads the header row to match the
sheet's widest used row before checking uniqueness — and a stray value (`46061.03`, looks like the
WF5-verification total from the 2026-08-09 session, apparently pasted into Transactions row 273
column X by accident) had widened the sheet's used range well past the real 12 columns, producing
many duplicate blank headers. Row 1 itself (`sh.row_values(1)`) was completely correct and
unique — the bug only showed up through the padded grid read, which is why it wasn't caught by
eyeballing the header row directly.

**Fix**: `sheets.py`'s `read_all()` now passes `expected_headers=HEADERS.get(tab_name)` (importing
the canonical `HEADERS` dict from `scripts/setup_sheets.py`, the existing single source of truth)
to `get_all_records()`. Per gspread's own source (read directly to confirm before trusting it):
`expected_headers` only requires the given list be a *subset* of the actual header row — it
doesn't require full-row uniqueness — so this survives stray padding without needing the sheet
cleaned up. Verified against the live Transactions sheet (279 rows read cleanly, real data intact)
and the full test suite (87/87 still pass). Pushed as `beb18eb`. The stray `46061.03` value itself
was left in place (flagged to the user, not deleted — a cosmetic cleanup, not a functional
problem now that the code tolerates it).

### WF6 build: no schema mismatch this time, unlike WF4/WF5
Diffed the `n8n-wf6-error-handler` skill runbook against `scripts/setup_sheets.py` per this
project's standard pre-build discipline — found nothing to fix. Unlike WF4/WF5, WF6 doesn't touch
any Sheets columns at all; it operates purely on the n8n error-trigger payload (workflow name,
node name, error message, execution ID/URL), so there was no schema-drift class of bug possible
here.

### Scope cut: Telegram alert only, no dead-letter file
The skill's full design includes a Drive dead-letter upload branch (Switch: Has Raw Data? →
upload full error payload as JSON) for preserving raw input data when a failure carries it. Asked
the user up front rather than assuming a folder existed — no `dead-letter/` Drive folder exists
yet, so built WF6 as Error Trigger → Code: Build Alert → Telegram only, with the omission
documented in the workflow's own sticky note (job, credentials, what's deliberately missing and
how to add it later) so a future session doesn't mistake it for an oversight.

### Build: `create_workflow` clean, landed in personal project again
Same pattern as WF3/WF4/WF5 — `create_workflow` built the 3-node graph in one call, confirmed via
immediate `get_workflow` re-fetch — id `YeWq5wH7cTboCQrL`. Landed in the user's personal n8n
project by default (same as every prior workflow's first build); user moved it to KRIMRAK and
registered it as the Error Workflow on WF1/WF3/WF4/WF5 manually via the UI. Reused WF4's exact
`telegram_lifeos_bot` credential (id `UpBn6PgGEv4G5kgo`, chatId `832207392`) — same convention as
every other workflow in this project.

### Real finding: manual "Execute workflow" test runs never reach the Error Workflow
The skill's own Test 1 (throwaway workflow, HTTP Request to `httpstat.us/500`, click "Execute
workflow" in the editor) failed silently — the throwaway workflow errored 3 times as expected
(`list_executions` confirmed `❌ error` each time), but WF6 had **zero** executions. This is not a
wiring mistake: n8n does not route manual/test-panel executions to a workflow's configured Error
Workflow, only real (production) executions — via an active trigger, webhook, schedule, or the
API — do. The skill runbook's Test 1 instructions are wrong for this n8n version and should be
corrected (not yet edited in the skill file itself, flagged here instead).

**Fix**: swapped the throwaway workflow's Manual Trigger for a Webhook node (path
`wf6-test-trigger`), had the user activate it via the UI (the `activate_workflow` MCP tool 415'd —
`unsupported media type application/x-www-form-urlencoded` — a connector bug, distinct from every
previously-reported `update_workflow` bug; `deactivate_workflow` worked fine for cleanup after),
then fired the real production webhook via `curl` against the URL the user copied from the node
panel (`https://veloxglobal.app.n8n.cloud/webhook/wf6-test-trigger` — first time this n8n
instance's actual hostname has been recorded in this file). `mcp__n8n__run_webhook` itself also
doesn't work in this environment (needs `N8N_WEBHOOK_USERNAME`/`N8N_WEBHOOK_PASSWORD` env vars
that aren't set) — direct `curl` was the working path.

### Clean verification
`list_executions` on WF6 showed exactly 1 new execution (`60432`, `✅ success`), started ~1 second
after the throwaway workflow's real production failure — genuine cause-and-effect, not
coincidence. The execution-detail API didn't return node-level output content to check
programmatically, so per this project's standing rule (don't trust a green status alone), asked
the user to confirm the actual Telegram message — user confirmed it arrived with the expected
`🚨 Workflow error / Workflow: My workflow 5 / Node: HTTP Request / Error: ...` content. Throwaway
workflow deactivated after (not deleted — leaving cleanup decisions to the user, consistent with
how `NIwD3iarrxwH36qj` was handled 2026-08-02).

### Loose ends for next session
- WF6's dead-letter Drive branch is unbuilt — add it once a `dead-letter/` Drive folder exists
  (folder ID needed), per the sticky note left on the workflow.
- The `n8n-wf6-error-handler` skill's Test 1 instructions (manual "Execute workflow" click) don't
  actually work on this n8n version — worth correcting the skill file itself at some point so the
  next project that uses it doesn't hit the same dead end.
- Same `NIwD3iarrxwH36qj` (archived, not deleted) and general-access-sheet loose ends from
  2026-08-02 remain untouched.
- The stray `46061.03` value in Transactions row 273 is harmless now (code tolerates it) but still
  worth deleting from the sheet directly next time the user is in there.
- **All 6 planned n8n workflows (WF1, WF3, WF4, WF5, WF6) are now built, verified, and active.**
  Only WF2 (Telegram AI agent) remains — deliberately last per the council's 2026-08-01 ordering.
  This is the last item in the original Phase 2+ plan.

### Next session — resume here
**Keyword: `WF2-build`**

Say "WF2-build" (or paste this section) to a new session on this project and have it, in order:
1. Read the `n8n-wf2-telegram-agent` skill for the workflow runbook.
2. Apply this project's now-standard pre-build discipline: diff the runbook's field/column
   references against `scripts/setup_sheets.py` (source of truth) before writing any node.
3. Build using `create_workflow` for the initial build, hand credential/project-move steps to the
   user via the n8n UI, re-verify every change with `get_workflow` — never trust a "done" without
   re-fetching.
4. Register WF6 as this workflow's Error Workflow too, same as WF1/WF3/WF4/WF5.
5. Test using a real webhook/trigger call (curl or the n8n UI's own test tools), not the editor's
   manual "Execute workflow" button — confirmed 2026-08-10 that manual test runs never reach the
   Error Workflow, so they're not a valid substitute for a real end-to-end test here either.
6. Update the status table and this file's session log the same way this session did.

---

## Session: 2026-08-10 (cont.) — Red team review: security, UX, insight depth

User deleted the stray `46061.03` value from Transactions row 273 (flagged end of prior session).
Ran a three-pass, self-adversarial review of the built system — security, then UX/edge cases
building on that, then categorization/insight depth building on both — grounded against the live
repo, GitHub Actions workflow, and n8n instance rather than a generic checklist. Full writeup
published as an artifact (title `krimrakora-redteam-review`, favicon 🔎) — this section is the
condensed record for future sessions.

### Iteration 1 — Security: real finding, not a generic list
Verified via `gh repo view`: **`rakaisa354/krimRakOra` is a public GitHub repository.** `CLAUDE.md`
itself — committed and versioned in it — documents the n8n Cloud hostname
(`veloxglobal.app.n8n.cloud`), every workflow ID, the service account email, Drive folder IDs,
credential display names, and the Telegram chat ID. None of that is a secret on its own (confirmed
`credentials.json`/`.env` were never committed, via `git log -- credentials.json .env`), but
together it's a working recon map of the automation surface. **Not fixed this session** — repo
visibility is the user's call, flagged as the top open item below.

Also found and fixed: `categorizer.py` interpolated raw, attacker-influenceable merchant text
(lifted straight from bank statement PDFs) directly into the Claude categorization prompt with no
sanitization — a crafted merchant name could have attempted prompt injection. Fixed with a
regex marker filter (`_sanitize_merchant` in `categorizer.py`) that routes suspicious merchant
strings to manual review instead of the API call, plus an explicit `<merchants>` untrusted-data
wrapper in the prompt itself. 6 new tests in `tests/test_categorizer.py` lock in the filter
behavior. Also re-flagged (not re-fixed, still open from 2026-08-02): the Transactions sheet's
general access was "Anyone with the link — Editor."

### Iteration 2 — UX: a real, fixable gap in what Telegram actually says
Read `.github/workflows/parse-statement.yml` directly and found the success/failure Telegram
messages were both generic regardless of outcome — `"✅ Statement parsed and written to Sheets."`
fires identically whether 60 real rows landed or a run silently wrote 0 new rows because
everything was a duplicate, and the failure message was a bare run-link with no reason.
`finance.py` already prints exactly the right summary (`"✓ N rows written, M duplicates
skipped"` / `"✗ ..."` on error) — it just never reached the user.

**Fixed**: both Telegram notify steps now capture the parse command's stdout/stderr via `tee
parse_output.log`, extract the real `✓`/`⚠`/`✗` line, and include it in the message via
`--data-urlencode` (switched from raw `-d text=` for safe multi-line handling). Critically,
preserved exit-code propagation through the new `tee` using `exit ${PIPESTATUS[0]}` on every
affected step — a `cmd | tee file` pipe silently returns `tee`'s exit code, not `cmd`'s, which
would have been exactly the class of false-success bug already fixed once, the hard way, in the
2026-08-01 session. Verified: YAML re-parses clean (`yaml.safe_load`), full test suite still
93/93 (87 + 6 new categorizer tests). Not yet tested against a real WF1 run — the fix is code-
verified, not live-verified; do that on the next real statement drop.

Also flagged, not built: no heartbeat if a GitHub Actions run never even starts after n8n's
dispatch (a gap neither WF1 nor WF6 can see, since it happens between two systems); Telegram
formatting is fragile-by-omission if `parse_mode` is ever turned on without an escaping helper
for merchant names.

### Iteration 3 — Insight depth: categorizer improved, report.py changes scoped not built
Read `report.py` directly: confirmed it's a strict single-month snapshot — the `Net_Worth` sheet
already has an unused `mom_change` column, i.e. the schema anticipated trend analysis that the
report logic never actually built. Also confirmed the pre-session categorizer prompt gave the
model zero guidance on gray-area spend (subscriptions, ambiguous merchant names) and no
instruction to calibrate confidence down for genuine ambiguity — every result looked equally
certain regardless of how uncertain the underlying merchant name actually was.

**Fixed**: `categorizer.py`'s prompt now states an explicit gray-area rule (recurring
subscriptions default to 'want' unless clearly a necessity) and instructs the model to prefer a
genuinely lower confidence score over guessing when ambiguous. **Scoped but not built** (flagged
for a future session rather than bundled into this one, per Surgical Changes): a month-over-month
delta section for `report.py` (reuses the existing `_month_filter` helper against the prior
month), and a deterministic Python heuristic — not a second LLM call, keeping the zero-recurring-
cost design intact — flagging any `budget_type` over 100% of allocation for 2+ consecutive months
with a plain-language next-action bullet.

### Loose ends for next session
- **Top open item**: decide whether to make the GitHub repo private (recommended) or split
  `CLAUDE.md`'s operational detail into a private doc — public exposure of the full automation
  map is the most severe finding from this review and wasn't fixed, only flagged, since repo
  visibility is a call for the user to make deliberately.
- Switch the Transactions sheet's general access off "Anyone with the link — Editor" (still open
  since 2026-08-02).
- The Telegram-message fix in `parse-statement.yml` is code/YAML-verified but not yet exercised
  against a real WF1 run — confirm on the next real statement drop.
- `report.py`'s month-over-month trend section and budget-overrun coaching heuristic are scoped
  (see Iteration 3 above) but not built.
- Add "validate `X-Telegram-Bot-Api-Secret-Token`" as a hard pre-activation checklist item when
  WF2 is eventually built (`n8n-wf2-telegram-agent` skill).
- Same `NIwD3iarrxwH36qj` (archived, not deleted) loose end from 2026-08-02 remains untouched.

### Next session — resume here
> **Superseded 2026-08-10** — WF2-build is done, see
> `## Session: 2026-08-10 (cont.) — WF2 built & verified` below for what actually happened. Left
> below, per this project's own "mention, don't delete" Surgical Changes rule.

Say **"WF2-build"** to pick up the last remaining planned workflow (see the 2026-08-10 WF6 session
above for the full handoff checklist), or **"security-hardening"** to work through the loose ends
above (repo visibility + Sheet access are the two real open risks from this review).

---

## Session: 2026-08-10 (cont.) — WF2 built & verified

Ran the `WF2-build` checklist. This is the last of the 6 planned n8n workflows — Phase 2+ is now
complete.

### Found and reused an abandoned June 2026 stub instead of creating a third duplicate
`ZwoPsgjdauO1atzi` ("WF2 — Telegram AI Agent") already existed, created 2026-06-01 — before
`finance.py`'s parsers/CLI even existed. It had empty HTTP bodies, an unconfigured Switch, zero
executions, and credentials borrowed from an unrelated project. Rebuilt in place via
`update_workflow` (the workflow already existed, so — consistent with WF5's finding — `update_workflow`
worked fine here; only *creating new* workflows from scratch needs `create_workflow`). This avoids
a third duplicate-name workflow, the exact confusion `NIwD3iarrxwH36qj` caused for WF1.

### Added a security gate not in the original skill runbook
A "Guard: Authorized User Only" IF node drops any Telegram message not from the owner's chat id
(832207392) before it reaches Claude or GitHub — this bot is publicly discoverable on Telegram
once named; without this gate, anyone who found it could trigger real GitHub Actions runs and
spend Claude API credits. Silent drop (no reply), so the bot doesn't reveal its existence to
strangers. Full Telegram `secret_token` header validation (per the 2026-08-10 red-team review's
loose end) turned out not to be directly wireable — n8n's native Telegram Trigger node doesn't
expose incoming headers the way a raw Webhook node does — so the chat-id allowlist serves as the
practical equivalent for a single-owner bot.

### Real bug 1 — quick-add path had no schema mismatch, but query-budget did
Diffed the skill runbook against the real GitHub Actions workflows (`quick-add.yml`,
`query-budget.yml`, both already existed) and `scripts/quick_add.py`/`scripts/query_budget.py`
before building, per this project's standard discipline. `quick_add.py` matched cleanly. But
`query_budget.py` had the exact same sign-filter bug already found and fixed in WF4/WF5's Code
nodes on 2026-08-09 (`amount_inr > 0`, excluding credits/reversals) — fixed the same way, by
summing all signed amounts. No dedicated test file existed for this script.

### Real bug 2 — the fix was edited but never pushed, caught by live testing
First real QUERY_BUDGET test ("how much did I spend this month?") replied with a total that,
independently re-summed against the raw sheet, didn't match — a real -₹45,000 BBPS bill-payment
credit was missing from the total. Root cause: the `query_budget.py` sign-filter fix above had
only been applied locally via `Edit` — never `git commit`/`git push` — so GitHub Actions was still
running the old, buggy code from `origin/main`. **Lesson, sharper than the existing "hand-verify
against real data" rule**: an `Edit` tool call changes the local file, not what's deployed; for
any file GitHub Actions executes, the fix isn't real until it's committed *and* pushed — verify
with `git log -1 -- <file>` after, not just that the local diff looks right. Committed as
`539f81e` and pushed. Also added a reconciling "Other/Uncategorized" line to the summary output,
since the categorizer's literal `budget_type: "Unknown"` (capital-U, case-sensitive) would
otherwise vanish from the visible breakdown while still counting toward the total — same class of
silent-gap issue as WF4's missing Budget row for `petty`.

### Real bug 3 — Claude had no ground truth for "today"
"how much did I spend in July?" replied "No transactions found for 2024-07" — two years off. Root
cause: the classification prompt never told Claude the actual current date, so it resolved
relative month references against its own internal assumption rather than this project's real
2026-08-10. Fixed by injecting `{{ $now.toISODate() }}` into the prompt as explicit ground truth.
Also (found in an earlier test) Claude returned `{"month": "current"}` for "this month" instead of
leaving it blank — fixed both in the prompt wording and, more robustly, with a defensive
`/^\d{4}-\d{2}$/` format guard on the GitHub: Query Budget node's `jsonBody`, so a future wording
drift in Claude's output can't silently break the query again.

### Clean verification, each step independently re-checked
1. "500 zomato dinner" → real row confirmed via a direct `read_all("Transactions")` re-read, not
   just the green n8n execution or the GitHub Actions log line.
2. "how much did I spend this month?" → after the push, total correctly showed -₹38,547 for
   2026-08, hand-verified against a direct sum of the real August rows (which matched exactly).
3. "how much did I spend in July?" → resolved to 2026-07 correctly after the date fix; total
   ₹57,579 across 257 rows, independently re-summed from the raw sheet and matched exactly
   (₹57,578.77).
4. "asdfgh" → UNKNOWN fallback replied correctly, confirmed via a real n8n execution.
5. Unauthorized chat id → not tested (hard to test solo); the Guard node's logic was verified by
   inspection (`get_workflow` re-fetch) but not exercised against a real message from a different
   Telegram account.

### Loose ends for next session
- The Guard node's chat-id gate is unexercised against a real unauthorized message — worth testing
  from a second Telegram account at some point, not blocking since the logic itself is simple and
  was verified by inspection.
- Same top-priority loose ends from the 2026-08-10 red-team review remain untouched: GitHub repo
  is still public, Transactions sheet is still "Anyone with the link — Editor".
- `NIwD3iarrxwH36qj` (archived, not deleted) loose end from 2026-08-02 remains untouched.
- **All 6 planned n8n workflows (WF1, WF2, WF3, WF4, WF5, WF6) are now built, verified, and
  active. Phase 2+ (the original n8n automation plan) is complete.** Future work is maintenance,
  the security-hardening loose ends above, or genuinely new scope the user decides to add.

### Next session — resume here
> **Superseded 2026-08-10** — see
> `## Session: 2026-08-10 (cont.) — review-correction flow + Income parsing` below for what
> actually happened. Left below, per this project's own "mention, don't delete" Surgical Changes
> rule.

Say **"security-hardening"** to work through the two remaining open risks (repo visibility + Sheet
access) from the 2026-08-10 red-team review — the last unaddressed items from that session. There
is no next planned workflow; new work from here is either hardening or new scope.

---

## Session: 2026-08-10 (cont.) — review-correction flow + Income parsing

User asked about `security-hardening` but declined both open items when asked directly (repo
stays public, Transactions sheet access unchanged — both still open, user's call). Redirected to
two real gaps the user flagged: low-confidence categorizations had no correction path, and the
`Income`/`Debts`/`Goals`/`Net_Worth`/`Vendor_Map` sheets were all still unused.

### Real bug found: confidence scores were never persisted
Confirmed via `finance.py`: a row's `_confidence` score was only ever printed to the CLI/Telegram
output (`⚠ N rows need category review`) and then discarded — never written to the sheet. Once a
low-confidence row landed in Transactions there was no way to find it again to fix it. Fixed by
tagging `notes` with `[review: confidence NN%]` at write time
([finance.py](finance.py:105)) whenever `_confidence < 80`, and adding `sheets.py`'s `update_row()`
plus a new `scripts/review_transactions.py` CLI that walks every tagged row and lets the user
correct category/subcategory/budget_type interactively, stripping the tag after. Verified with a
mocked-sheet run (correction applied, tag stripped, untagged rows skipped) — full suite still
93/93. **Scope note**: only catches rows written after this fix; past low-confidence rows already
in the sheet were never tagged and aren't retroactively covered.

### Real bug found: a real July statement drop silently produced 0 rows
While scoping Income parsing, the user mentioned they'd already dropped a July statement through
WF1 and it "got parsed." Checked the live GitHub Actions run
(`31383857286`) — it reported `✓ 0 rows written, 0 duplicates skipped`, a **false success**: the
file (`40XXXXXXX437.pdf`) is the user's **Kotak savings account** statement, not the Kotak
Cashback+ credit card, but `detect_card_type()` in `parsers/__init__.py` matches on the bare
substring `"Kotak Mahindra Bank"`, which appears in both statement types. It silently ran through
the Kotak *card* parser, found zero matching lines (different format entirely), and reported
success with nothing written and no warning anywhere. Downloaded the actual file from Drive (via
`scripts/download_drive_file.py` and the file ID from the Action's log,
`1nu13nWBDwy_JYdLIMfLnjuH5oTGFYXmK`) and decrypted it locally to confirm.

Also found via `dump/kotak/*437*`: this exact savings-account statement has been sitting in the
dump folder since April, unused — the Kotak *card* parser was correctly built against the other
Kotak file (`94XXXXXXXXXXX255`, "Cashback+ Credit Card"), and nobody had noticed the second Kotak
account existed until this session.

### Income parsing — built and verified against 4 real months
User confirmed scope: extract only real income (salary NEFT credits) into `Income`, not a full
ledger of the account's other debits (UPI transfers, mutual-fund SIPs, CC bill payments via CRED
Club) — those are either already tracked via the credit cards or not spend at all. User named the
two known salary sources: **KALS BREWERIES** (verified, appears in every real statement checked)
and **RENGANAYAKI AGENCIES** (per the user's report — not yet seen in any real statement, kept in
the employer list unverified, flag if/when a statement with that name actually comes through).

Built `income_parser.py`: `is_kotak_savings_statement()` detects the statement type (checks for
`"Savings Account Transactions"` + `"Account Type  Savings"`, both present, neither in the CC
statement), and `extract_kotak_savings_income()` finds NEFT credit lines mentioning a known
employer and reads the deposit amount. **First implementation had a real bug**: it segmented the
raw text into per-transaction blocks bounded by the *next* transaction's start marker (or
end-of-text for the last transaction) and took the second-to-last money value in the block as the
deposit — this worked for months where the salary line wasn't the statement's last transaction,
but for July (where it was) the block ran past the transaction into the next page's footer/header
text, and the "second-to-last number" picked up the running balance instead of the real deposit
(₹2,13,549.72 instead of ₹1,83,842.00). Fixed by using a small fixed-size window (250 chars) right
after each employer-name match instead of a variable-length block — re-verified against April,
May, June, and July: ₹1,69,894 / ₹1,83,842 / ₹1,83,842 / ₹1,83,842, one salary credit per month,
matching by inspection of the raw statement text each time.

Wired into `finance.py`'s `parse --pdf`: `is_kotak_savings_statement()` is now checked *before*
`detect_card_type()`, so a Kotak savings statement routes to the income extractor and writes to
`Income` (with its own dedup on `(date, source, amount)`) instead of silently mis-parsing as a
card statement. 5 new tests in `tests/test_income_parser.py` (real verbatim excerpt from the July
statement, per this project's standing fixture convention) + full suite 98/98.

**Clean verification**: dry-run against the real July statement showed exactly one row
(`2026-07-31 | Kals Breweries | ₹183842.00`); user approved a real write; independently re-read
`Income` via a fresh `read_all()` call afterward and confirmed exactly that one row, matching
exactly — the first real row that sheet has ever had.

**What this does NOT fix**: the underlying `detect_card_type()` false-positive risk (a bare
bank-name substring match) still exists for any other bank that ever has both a card and a
savings product sharing the same name string — not urgent today since Kotak is the only such
overlap, but worth knowing if a 6th card is ever added.

### Loose ends for next session
- RENGANAYAKI AGENCIES is an unverified employer pattern — confirm against a real statement
  whenever one shows up.
- `Debts`, `Goals`, `Net_Worth`, `Vendor_Map` are still unused (Income now has real data via this
  session's work, but the other four still have zero real rows) — not addressed this session,
  flagged by the user, not yet scoped.
- Only Kotak's income is automated; the user's other income sources (if any) still require manual
  entry into `Income`.
- Same security-hardening loose ends from 2026-08-10 (repo visibility, Sheet access) remain open —
  user declined both when asked directly this session.
- `NIwD3iarrxwH36qj` (archived, not deleted) loose end from 2026-08-02 remains untouched.

### Next session — resume here
> **Superseded 2026-08-10** — see `## Session: 2026-08-10 (cont.) — Kotak savings full ledger`
> below for what actually happened. Left below, per this project's own "mention, don't delete"
> Surgical Changes rule.

Say **"security-hardening"** for the still-open repo/Sheet-access items, or bring a real
statement/data for `Debts`/`Goals`/`Net_Worth`/`Vendor_Map` to start populating those sheets for
real.

---

## Session: 2026-08-10 (cont.) — Kotak savings full ledger

User re-uploaded the same July Kotak savings statement to the WF1-watched Drive folder, asking to
"check it" — turned out to be a duplicate of the file already processed for Income earlier this
session (confirmed by downloading and decrypting it: identical content, `Account Statement 01 Jul
2026 - 31 Jul 2026`, same account `407010101437`). Not a new debt statement as first assumed from
the user's "bring a statement for Debts" framing.

### Scope changed mid-session: user wants the full ledger, not just salary
User clarified: all 4 credit cards are already in Transactions; what's actually missing is the
**savings account's own income and spend**, not just the salary credit already extracted. This
supersedes the 2026-08-10 (earlier) session's deliberate "income only, not a full ledger" scope
call — the user re-scoped it themselves this time, with real detail on how to classify the
ambiguous parts:
- **CRED Club** lines are usually credit card bill payments but not always ("shopping or parking
  or something else too") — don't auto-exclude, write as unknown/flagged for later manual
  categorization.
- **K Radha Gouri** transfers (she's the account's registered nominee) go both directions —
  sometimes she reimburses the user for a card payment, sometimes it's something else — also
  flagged, not guessed.
- The large **"Ins Debit"/"Pyt Loan" GLN-tagged** lines (~₹4.4L) are a **gold loan** — confirmed
  by the user, not something to guess a `Debts` row from off one month's cash flow.
- Personal UPI payments to individuals (Jai Medicals, Chai Kings, etc.) are real spend and should
  run through the normal categorizer, same as card spend.

### Built `savings_ledger.py`
`_parse_all_lines()` parses every transaction row (not just salary-matching ones) and derives each
row's **signed** amount from the delta between consecutive printed running balances — the
underlying PDF has separate Withdrawal(Dr.)/Deposit(Cr.) columns that `pdftotext` flattens into a
single number with no debit/credit marker, so direction can't be read off the line itself.
`classify_savings_transactions()` buckets every row into salary/sip/cred_club/family/spend/loan by
description keyword, in priority order (checked salary/sip/cred_club/family before the generic
`UPI/` fallback, so those don't get miscategorized as plain spend).

**Real bug caught while writing the test, not while building the feature**: the first test fixture
hand-trimmed the statement down to a handful of representative transactions (skipping ranges like
4-6, 8, 10-21) to keep the test file short. This silently broke the balance-delta math — the
delta between two non-adjacent real transactions includes every skipped transaction's effect too,
so multiple assertions failed with values that were real historical balances but wrong for the
individual (spliced) rows being tested. This is exactly the class of fixture bug this project's
own convention (verbatim excerpts, not hand-cleaned) exists to catch — caught it here, not in
production, because the assertions were checked against independently-known real values rather
than accepted on faith. Fixed by using the full, unmodified 53-transaction statement as the test
fixture instead of a hand-picked subset — `tests/test_savings_ledger.py`, 8 tests, all passing,
including a full-statement reconciliation check (`sum of all deltas == closing balance - opening
balance`).

### Wired into `finance.py`
`_parse_kotak_savings_full()` replaces the earlier income-only branch: still writes salary to
Income first (`_parse_kotak_savings_income`, unchanged), then writes SIP debits
(`Investment/SIP/save`, deterministic), CRED Club and family-transfer rows (`Unknown` category,
`[review: ...]`-tagged in `notes`, reusing the review-flow mechanism built earlier this session),
and personal UPI spend (run through the real `categorize_transactions()`, same Claude pipeline
every card parser uses) — all under `card_account = "Kotak Savings"` in `Transactions`, with the
same `(date, merchant, amount_inr)` dedup as every other parser. Loan-linked lines are printed to
the console/Telegram output only, never written to any sheet.

### Clean verification
Dry-run against the real July statement showed 48 new rows (0 income — already written earlier
this session, correctly deduped) and 4 loan lines reported separately; user approved a real write.
Independently re-read `Transactions` afterward: exactly 48 rows with `card_account = "Kotak
Savings"`, summing to ₹135,966.76, 42 of them carrying a `[review: ...]` tag — matched the CLI
output exactly.

### Loose ends for next session
- The gold loan found in this statement (GLN 4228809 / 4805528, ~₹4.4L) is not yet in `Debts` —
  needs the user's real loan terms (principal, interest rate, current outstanding, EMI/due date)
  before it can be entered; a single month's disbursement/insurance-debit pair isn't enough to
  reconstruct that safely.
- This pipeline only covers Kotak's savings account; if the user has other bank accounts, they'd
  need the same statement → `is_<bank>_savings_statement()` → `savings_ledger`-style treatment
  built fresh, verified against a real statement the same way this one was.
- `Goals`/`Net_Worth`/`Vendor_Map` are still unused — unchanged from the earlier session's note.
- Same security-hardening loose ends from 2026-08-10 (repo visibility, Sheet access) remain open.
- `NIwD3iarrxwH36qj` (archived, not deleted) loose end from 2026-08-02 remains untouched.

### Next session — resume here
> **Superseded 2026-08-10** — see
> `## Session: 2026-08-10 (cont.) — reviewed all 48 Kotak Savings rows` below for what actually
> happened. Left below, per this project's own "mention, don't delete" Surgical Changes rule.

Bring the gold loan's real terms (principal, rate, outstanding, EMI/due date) to populate `Debts`
for real, or say **"security-hardening"** for the still-open repo/Sheet-access items.

---

## Session: 2026-08-10 (cont.) — reviewed all 48 Kotak Savings rows

Worked through the 42 rows flagged by the previous session's Kotak-savings-ledger write.

### `scripts/review_transactions.py` had two real bugs, both fixed before use
1. Its filter only matched `[review: confidence NN%]` — the 14 rows tagged with the CRED
   Club/Radha Gouri review text (a different message, from `finance.py`'s
   `_parse_kotak_savings_full()`) never showed up. Broadened `REVIEW_TAG` and the filter to match
   any `[review: ...]` tag, and printed the actual flag text per row so the user can tell at a
   glance why something's flagged.
2. It was missing the `sys.path` fix every other `scripts/*.py` needs to import root-level
   modules (`sheets`, `scripts.setup_sheets`) — running it standalone crashed with
   `ModuleNotFoundError: No module named 'sheets'` the first time it was actually run outside a
   test. Neither bug was caught when the script was built earlier this session because it was
   only smoke-tested via a mocked mid-conversation call, never actually executed for real.

### Interactive CLI doesn't work through this tool — switched to chat-driven review
Tried running `scripts/review_transactions.py` for the user via the agent's own shell — it hung on
the first `y/n` prompt and aborted, since the tool executes one command and returns rather than
holding an interactive session open for someone to type into. The user ran it themselves in their
own terminal for a first pass (5 rows fixed that way), then switched to doing the rest directly in
chat: the assistant listed each flagged row, the user described what it actually was in plain
language, and the assistant wrote the correction via `sheets.update_row()` directly — bypassing
the CLI tool entirely for the remaining 37.

### Real detective work, not just data entry
Several of the 6 K Radha Gouri rows turned out to be reimbursements identifiable by matching them
against same-day amounts elsewhere in the statement, not just user-supplied labels — found before
asking the user, by comparing the full transaction list already extracted by `savings_ledger.py`:
- 14 Jul: two Radha Gouri credits (₹2,000 + ₹1,400 = ₹3,400) against the same day's CRED Club
  payment (₹3,389) — close enough to be the same reimbursement (small UPI-fee-sized gap).
- 15 Jul: Radha Gouri credit ₹3,000 exactly matches that day's CRED Club payment ₹3,000.
- 19 Jul: Radha Gouri credit ₹2,185 exactly matches that day's Amura Nutritio (health supplement)
  purchase ₹2,185 — not a CC bill this time, categorized to match the purchase it offsets
  (`Health & Wellness/Supplements`) instead, so the reimbursement nets the real spend to zero in
  that budget bucket rather than showing up as unexplained income.
- 24 Jul: Radha Gouri credit ₹4,200 exactly matches that day's CRED Club payment ₹4,200.
- 23 Jul: Aryan S Jain sent ₹1,200 in, and K Radha Gouri received ₹1,200 out, same day — user
  confirmed this was money forwarded straight through, not real spend or income; both rows
  categorized `Transfer/Pass-through` with a blank `budget_type` so neither counts toward any
  budget bucket.

This resolved both sides of each pair at once (the CRED Club row → `Credit Card
Payment/Bill Payment/debt`, the matching Radha Gouri row → the same category, or the offset
purchase's category for the Amura Nutritio case) — the user never had to manually confirm the
pairing, only the parts genuine ambiguity required (e.g. the ₹31,250 CRED Club payment on 22 Jul,
which had no matching same-day transfer and the user themselves wasn't fully sure was a CC bill).

### A day-of-week heuristic caught a real gap in the user's own guess
User offered "Kamalraj M is probably the temple priest, check if it's a Sunday" as a heuristic
that had already worked for two other names (Mr R Sivasanga, Savutha K — both correctly landed on
19 Jul, a Sunday). Checked via `datetime.date.fromisoformat(...).strftime('%A')`: Kamalraj M's
transaction was on 25 Jul, a **Saturday** — the heuristic's own precondition didn't hold, so held
off on categorizing rather than applying a pattern the user had explicitly conditioned on a fact
that turned out false for this specific row. Asked directly instead of guessing; turned out to be
Rapido (along with Muthukumaran M, same day) — both `Transport/Auto-Cab-Parking/need`.

### Clean verification
Independently re-read `Transactions` after each batch of writes (24 rows, then 11, then 2) and
confirmed the flagged count dropped 42 → 13 → 2 → 0 exactly matching what was applied each time,
not just trusting the update calls succeeded silently. Full test suite still 106/106 (no code
changed except the two `review_transactions.py` bug fixes, already committed and pushed in the
prior turn).

### Loose ends for next session
- Two categorizations were applied with acknowledged uncertainty, left in `notes` rather than
  silently treated as confirmed: the ₹31,250 CRED Club payment (22 Jul) — user said "I think yes,
  I'm not sure" — and the ₹1,500 credit from Subhathra Venk (25 Jul) — user said "not sure, maybe
  some vendor," categorized generically as `Refund/Reimbursement`. Worth a second look if the user
  ever gets more certainty on either.
- New categories introduced this session (`Credit Card Payment`, `Spiritual & Wellness`,
  `Transport`, `Family`, `Hobbies`, `Shopping`, `Refund/Reimbursement`, `Transfer`, `Subscriptions`)
  aren't yet seeded in the `Categories` sheet (57 rows, established in Phase 0) — the categorizer's
  Layer 1 Vendor_Map lookup won't recognize these merchant names next time they recur (K Swathithra,
  Rani M, Kandasamy G, Vasudevan R, etc. are all likely to repeat monthly). Consider training
  `Vendor_Map` with these mappings via the `vendor-map-train` skill so future Kotak Savings imports
  don't need this same manual pass.
- The gold loan (GLN 4228809/4805528) is still not in `Debts` — same open item as the prior
  session, needs real loan terms from the user.
- Same security-hardening and `NIwD3iarrxwH36qj` loose ends from earlier 2026-08-10 sessions
  remain untouched.

### Next session — resume here
Train `Vendor_Map` with this session's new merchant→category mappings so they don't need
re-categorizing every month, bring the gold loan's real terms to populate `Debts`, or say
**"security-hardening"** for the still-open repo/Sheet-access items.
