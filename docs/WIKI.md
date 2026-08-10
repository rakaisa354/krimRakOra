# krimRakOra — Project Wiki

A human-readable history and knowledge base for this project. `CLAUDE.md` is the
machine-context file Claude reads at the start of every session (status table, file index,
conventions); this file is the narrative version — what the project is, why it exists, and how
it got to where it is. Update it when something worth remembering happens; it's fine for this to
lag CLAUDE.md's session-by-session detail.

---

## What this project is

A zero-recurring-cost personal finance controller for an India-based user currently in an active
credit-card debt payoff phase. It tracks every transaction across 4+ credit cards, converts
foreign-currency spend to INR, categorizes spend automatically, runs a hybrid avalanche+snowball
debt payoff plan, and produces monthly net-worth and spend reports — all without paying for any
new SaaS. The whole stack is: Python parsers → Google Sheets (as the database) → n8n Cloud (free
tier automation) → Telegram (the interface).

The "why zero recurring cost" constraint isn't incidental — it's a first-class design rule. Any
proposal that introduces a paid service gets rejected on sight unless there's no free alternative
(see "Decisions" below for the one time this was tested).

## How it's built, phase by phase

**Phase 0–1 (done):** Project scaffolding, Google Sheets with 9 tabs, and five bank-specific
statement parsers (ICICI, RBL, SBI, Scapia, Kotak), each converting a statement into the same
unified transaction schema.

**Phase 1.5–1.7 (done):** The parsers originally expected clean markdown input, but real
statements arrive as password-protected PDFs. Three modules closed that gap: PDF decryption
(pure Python, no third-party API — the statement text never leaves the machine), PDF-to-markdown
extraction (one regex-based extractor per bank, each with its own quirks — see "Bank-specific
gotchas" below), and CLI wiring so `finance.py parse --pdf <file>` goes from an encrypted PDF
straight to a Google Sheets row in one command.

**Phase 2 (n8n WF1 — automating statement ingestion, done 2026-08-02):** A statement PDF lands in
a watched Google Drive folder, n8n notices it, tells GitHub Actions which file to grab, GitHub
Actions downloads it, decrypts and parses it, writes to Sheets, and Telegram confirms. Getting
there took three real attempts (see "Decisions" and the CLAUDE.md session notes for 2026-08-01
and 2026-08-02) — a wrong-design workflow, a GitHub API payload bug, an unpushed-commit scare, a
literal tab character silently breaking the whole GitHub Actions workflow file, and a Google
Sheet the write service account was never actually shared on. Verified end-to-end with a real
statement on 2026-08-02: 60 real transaction rows landed in the Transactions sheet from a genuine
Drive-upload-to-Telegram-confirmation run.

```mermaid
flowchart LR
    A["Statement PDF\ndropped in Drive"] --> B["n8n Drive Trigger\n(polls watched folder)"]
    B --> C["n8n: Trigger GitHub Parse\n(repository_dispatch,\nfile_id + filename only)"]
    C --> D["n8n: Telegram Notify\n📥 received"]
    C --> E["GitHub Actions\nparse-statement.yml"]
    E --> F["download_drive_file.py\n(service account, drive.readonly)"]
    F --> G["finance.py parse --pdf\ndecrypt → extract → parse → categorize"]
    G --> H["Google Sheets\nTransactions tab\n(service account, Editor)"]
    G --> I["Telegram\n✅ parsed / ❌ failed\n(truthful exit code)"]

    style A fill:#e8f4fd,stroke:#1a73e8
    style H fill:#e6f4ea,stroke:#188038
    style I fill:#e6f4ea,stroke:#188038
```

**Phase 3 (n8n WF3/4/5 — all three done):** Scheduled jobs — daily FX
rate sync, daily spend summary to Telegram, monthly report generation. WF3 (daily FX sync, 6am
IST) fetches rates for 8 currencies and appends them to the `FX_Rates` sheet, with a fallback
branch that carries forward yesterday's rates and alerts on Telegram if the API call fails.

```mermaid
flowchart LR
    A["Schedule Trigger\n30 0 * * * (6am IST)"] --> B["HTTP GET\nexchangerate-api.com"]
    B -->|success| C["Code: parse & compute\nrate_to_inr, 8 currencies"]
    B -->|error| D["Sheets Read\nlast known rates"]
    C --> E["Google Sheets\nFX_Rates tab (append)"]
    D --> F["Code: carry forward\nyesterday's rates"]
    F --> E
    F --> G["Telegram\n⚠ sync failed, using\nyesterday's rates"]

    style A fill:#1a2b22,stroke:#3ecf8e
    style E fill:#1a2b22,stroke:#3ecf8e
    style G fill:#2b2416,stroke:#e8b64c
```

Getting there took one real bug: the Sheets Append node's `appendOrUpdate` operation, matched on
`(date, currency_code)`, behaved like a date-only match in practice — since all 8 currencies in a
batch share the same date, each one silently overwrote the previous one's row instead of inserting
its own, losing data (a missing USD row, a duplicated JPY row) despite the execution reporting
success. Caught by independently re-reading the sheet rather than trusting the green execution
status — the same lesson WF1 taught with its false-success Telegram messages. Fixed by switching
to a plain `append` (upsert semantics weren't actually needed for a once-daily job). See
`CLAUDE.md`'s `## Session: 2026-08-02 (cont.) — WF3 built & verified` for full detail.

WF4 (daily spend summary, 9pm IST) reads today's Transactions and this month's Budget, aggregates
spend by budget_type, flags any category over 80% of its weekly allocation, and sends a Telegram
digest (or a "no spend today" message).

```mermaid
flowchart LR
    A["Schedule Trigger\n30 15 * * * (9pm IST)"] --> B["Sheets Read\nBudget tab"]
    B --> C["Sheets Read\nTransactions tab\n(executeOnce: true)"]
    C --> D["Code: aggregate by\nbudget_type, flag >80%\nweekly spend"]
    D --> E{"has_transactions?"}
    E -->|yes| F["Telegram\n📊 daily digest"]
    E -->|no| G["Telegram\n✓ no spend today"]

    style A fill:#1a2b22,stroke:#3ecf8e
    style F fill:#1a2b22,stroke:#3ecf8e
    style G fill:#1a2b22,stroke:#3ecf8e
```

Three real bugs surfaced during testing, none visible from a green execution alone. First, a
schema mismatch caught *before* any node was built: an `llm-council` review (run at the user's
request) diffed the skill runbook's Code node against CLAUDE.md's own schema table and found it
aggregating on `needs/wants/savings` (plural) when the sheet actually stores
`need/want/save/debt/petty` (singular) — unfixed, three of five categories would have silently
read ₹0 forever. Second, wiring the two Sheets Read nodes in parallel into the Code node raced:
n8n fires a node as soon as its *first* predecessor finishes, not all of them, so the Code node ran
before Budget had loaded. Fixed by chaining them sequentially. Third — and introduced by that very
fix — once the Budget sheet had 5 real rows, the downstream Transactions read re-executed once
*per incoming Budget item* (n8n's default fan-out behavior), inflating every total by exactly 5x.
Diagnosed by counting: 5 output rows to Budget, 5x inflation, no coincidence. Fixed with
`executeOnce: true`. Verified clean afterward with a real ₹500 test transaction and its deletion,
confirming both the digest and the no-spend paths against hand-summed real data — not just a
plausible-looking Telegram message. See `CLAUDE.md`'s `## Session: 2026-08-09 — WF4 built &
verified` for full detail.

WF5 (monthly report, 1st of month 8am IST) reads last month's Transactions, Income, Debts, Goals,
and Net_Worth, and sends a Telegram summary plus a full markdown report uploaded to Drive.

```mermaid
flowchart LR
    A["Schedule Trigger\n30 2 1 * * (8am IST)"] --> B["Code: determine\nreport month"]
    B --> C["Sheets Read x5\n(sequential chain)\nTransactions -> Income -> Debts\n-> Goals -> Net_Worth"]
    C --> D["Code: build report\n(net all amount_inr,\nno sign filter)"]
    D --> E["Convert to File\n+ Drive Upload"]
    E --> F["Telegram\nsummary + Drive link"]

    style A fill:#1a2b22,stroke:#3ecf8e
    style F fill:#1a2b22,stroke:#3ecf8e
```

Building it followed the same council-audited process WF4 established. Diffing the skill
runbook against `scripts/setup_sheets.py` before any node was built caught four schema
mismatches at once (Debts, Net_Worth, Goals, Income field names) — the same class of bug as
WF4's `needs/wants/savings` mistake. A first wiring redesign then reproduced WF4's exact
race-condition bug by fanning all five Sheets Read nodes in parallel with the (wrong) reasoning
that no Merge node meant no race; corrected to WF4's proven sequential-chain fix before build.

Two real bugs surfaced during testing. First, `getAll` on an empty Debts/Goals sheet returned a
single truthy-but-blank row rather than an empty array, defeating the code's `priorityDebt ? ...`
fallback and producing `NaN%` in the report — fixed by filtering out rows with no
`debt_name`/`goal_name`. Second, and more consequential: the Transactions filter excluded
`amount_inr <= 0` rows, but real statements contain charge/reversal/remainder triplets (a
purchase immediately reversed, then re-charged at the true net amount, same pattern as Kotak/
ICICI EMI conversions) — filtering to positives only double-counted every reversed charge as
real spend. The first "verified" pass missed this because hand-summing the code's own filtered
output only confirms internal consistency, not correctness; the user caught it by independently
computing the expected net total from first principles and finding it didn't match. Fixed by
removing the sign filter entirely — verified against real July data (`-32564.71`), then again
against a full real dataset from all 4 cards after the user finished loading actual statements
(`+46061.03`, matching a formula-based independent sum exactly). The identical filter bug was
then found and fixed in WF4 proactively, same session, before any live incident. See `CLAUDE.md`'s
`## Session: 2026-08-09 — WF5 built & verified` and the following sessions for full detail,
including the final lesson: verify sheet totals with a formula, not a manual row selection — this
project's Transactions sheet is append-only by import batch per card, not sorted by date, which
makes eyeballing genuinely unreliable.

**Phase 4 (done):** Debt payoff planning (hybrid avalanche/snowball, pays off small balances
first for psychological wins, then attacks highest-interest debt) and net worth tracking.

**Phase 5 (done):** Test hardening — 87 tests, all passing.

**WF2 (Telegram AI agent — not started, deliberately last):** A conversational interface over
the data (quick-add transactions, ask budget questions) using Claude Haiku. Scheduled last
because it's the highest-effort, lowest-urgency piece — the core pipeline (statement in, row in
Sheets out) has to be trustworthy before a chat layer sits on top of it.

## Decisions worth remembering

**Rejected: the Supabase/LlamaParse/Next.js pivot (2026-07-06).** Partway through, a much
heavier redesign was floated — a hosted FastAPI decrypt service, LlamaParse/OpenAI for
extraction, a Supabase database, a LangChain text-to-SQL agent, and a Next.js frontend. It was
red-teamed and rejected: it introduces recurring cost the debt-kill phase doesn't want, it would
ship full bank statement text to third-party APIs (violating the standing rule to strip
statement text before any Claude API call, let alone an unrelated third party), and it largely
duplicates work already done and tested (the parsers, Sheets-as-database, Telegram-as-interface).
The one thing kept from the proposal was its discipline — build one module at a time, test before
moving on — which was already consistent with how the project works.

**Rejected: financial data connectors and Cowork's finance plugins (2026-08-01).** An LLM council
review raised the question of whether Plaid-style bank connectors, or Cowork's "finance" /
"financial-analysis" plugins, were worth adopting. Both were evaluated and rejected for the same
underlying reason as the Supabase pivot: they're built for corporate or investment-banking
workflows (portfolio analysis, institutional reporting), not personal debt tracking, and they'd
introduce third-party access to financial data and/or recurring cost that the existing
statement-PDF pipeline avoids entirely.

**Approved instead:** keep extending the existing free stack. This has held for the whole project
so far — every phase builds on Sheets + n8n + Telegram + local Python rather than replacing any
of them.

## Bank-specific gotchas (useful if adding a new card later)

Each bank's PDF text extraction turned out to have its own edge case, discovered only by
inspecting real (not synthetic) statement text:

- **ICICI** — reward/amount text can bleed together from the statement's chart legend; the
  extractor takes the *last* match in each blob rather than the first.
- **RBL** — the raw extracted text drops the visual "CR" credit marker entirely; credits are
  instead detected by keyword (PAYMENT, CASHBACK, REFUND, etc.).
- **SBI** — EMI instalment IGST lines print with no date of their own in the raw text (they're a
  PDF sub-line of the prior transaction) and had to be attached back to that transaction's date
  carefully, without false-matching the statement's terms-and-conditions footer.
- **Scapia** — merchant names run together with no spaces in the raw extracted text, and a
  repeated page-header block interleaves at every page break.
- **Kotak** — the one true surprise: EMI-converted purchases are *reversed* in the same statement
  by a matching negative line, so counting both would double-count spend. This is the *opposite*
  of how ICICI and Scapia handle EMI (they count the full purchase once, and the EMI breakdown is
  just informational). Verified against the statement's own printed totals — always do this for
  any new EMI-handling bank rather than assuming the last bank's pattern holds.

**Axis and Emirates NBD were dropped from scope** — the Axis files turned out to be
savings-account statements with zero transactions (no actual Axis credit card in use), and
Emirates NBD was confirmed unnecessary by the user.

## What tripped things up operationally

- **iCloud sync slowness.** The project folder lives under a Documents path with iCloud
  "Desktop & Documents Folders" sync on, which lazily fetches files and caused severe slowness
  (and, separately, "cloud placeholder" errors when Claude tried to read files that iCloud hadn't
  downloaded locally yet). The virtual environment was moved out of the synced folder as a fix;
  `brctl download` is the recurring workaround for placeholder files.
- **A near-miss with two months of unpushed work.** On 2026-08-01, routine verification turned up
  that the last several weeks of real feature work — PDF decryption, all five bank extractors,
  the debt/net-worth modules, the WF1 redesign — existed only in the local working tree and had
  never been pushed to GitHub. This is why GitHub Actions kept silently running an old version of
  the parse workflow no matter what got "fixed" locally. Recovered by carefully staging and
  pushing a curated commit. Worth treating as a standing lesson: check `git status` against
  `origin/main` periodically, not just when something breaks.
- **The n8n MCP connector's `update_workflow` tool is unreliable — confirmed broken three separate
  times** (2026-08-01, twice on 2026-08-02) with the same `settings must NOT have additional
  properties` error, regardless of payload. `create_workflow` (for brand-new workflows) works
  fine and was used to build WF3. Any *edit* to an existing workflow still has to go through the
  n8n UI by hand, with a `get_workflow` re-fetch afterward to confirm it actually saved — never
  trust a UI "done" on its own.

## Current state and what's next

As of 2026-08-10, the statement-ingestion pipeline (WF1) and all three Phase 3 scheduled jobs
(WF3 daily FX sync, WF4 daily spend summary, WF5 monthly report) are done and verified. WF1: a
real statement PDF dropped in Drive goes all the way to a real row in the Transactions sheet and
a truthful Telegram confirmation, with no manual steps in between. WF3: a daily 6am IST cron
(active in n8n) fetches and writes 8 currencies' INR rates to the `FX_Rates` sheet, with a
tested-but-not-yet-fired fallback path for API failures. WF4: a daily 9pm IST cron (active in
n8n) reads today's spend and this month's Budget, and sends a truthful Telegram digest —
verified against real hand-summed data on both the has-spend and no-spend paths. WF5: a monthly
1st-of-month 8am IST cron (active in n8n) reads last month's Transactions/Income/Debts/Goals/
Net_Worth and sends a Telegram summary plus Drive-uploaded report — verified against the user's
full real July dataset across all 4 cards, matching an independent formula-based sum exactly
(₹46061.03). WF6 (error handler) is now also done and verified: a Telegram alert fires whenever
any of WF1/WF3/WF4/WF5 fails, confirmed via a real production webhook failure (not the editor's
manual "Execute workflow" button, which turned out not to reach a workflow's Error Workflow at
all on this n8n version). **All 6 originally-planned n8n workflows are now built and active** —
only WF2 (Telegram AI agent) remains, deliberately last per the 2026-08-01 council ordering.

A same-day security/UX/insight-depth review (2026-08-10) found the project's most serious open
risk to date: **the GitHub repo is public**, and `CLAUDE.md` — checked into it — documents the
full automation surface (n8n hostname, workflow IDs, service account email, Drive folder IDs).
Not fixed yet; it's the top item on the next-session list, alongside the still-open Transactions
sheet link-editable setting. The same review found and fixed a real prompt-injection gap in the
categorizer (merchant text was interpolated into the Claude prompt unsanitized) and a real UX gap
in WF1 (Telegram success/failure messages were generic regardless of what actually happened,
even though `finance.py` already computed the real summary). See `CLAUDE.md`'s
`## Session: 2026-08-02`, `## Session: 2026-08-02 (cont.) — WF3 built & verified`,
`## Session: 2026-08-09 — WF4 built & verified`, `## Session: 2026-08-09 — WF5 built & verified`,
`## Session: 2026-08-10 — WF6 built & verified, Kotak parse bug fixed`, and
`## Session: 2026-08-10 (cont.) — Red team review` sections for full detail, including follow-up
items worth doing next time someone's in the n8n UI or Google Sheets: hard-deleting the
already-archived dead WF1 duplicate, exercising WF3's and WF4's untested error/warning branches
for real, testing WF5's Debt Avalanche and Goals Progress sections against real non-empty data,
tightening the Transactions sheet's "anyone with the link can edit" sharing setting, and deciding
whether to make the GitHub repo private.
