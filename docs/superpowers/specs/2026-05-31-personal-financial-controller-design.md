# Personal Financial Controller — Design Spec
**Date:** 2026-05-31  
**Status:** Approved for implementation planning  
**Project:** krimRakOra

---

## Context

The user is living in India, carrying significant debt across 5 credit cards, gold loans, and personal commitments. Two bank accounts (one salary, one dormant). Goal: build a personal financial controller that tracks every rupee, kills debt aggressively, forces savings, and creates a framework for becoming a global citizen / digital nomad. Multi-currency from day one (INR, USD, GBP, EUR, SGD + any future currency). No custom app — automation-first using tools already being paid for.

**Guiding philosophy:** Personal Financial Intelligence — know cash flow, fight inflation, control debt, invest, build wealth. Every rupee assigned a job.

---

## Stack

| Layer | Tool | Role |
|---|---|---|
| Automation | n8n Cloud | Workflow orchestration |
| Interface | Telegram Bot | All user interaction |
| Storage | Google Sheets | Lightweight database (8 sheets) |
| File input | Google Drive | Statement MD uploads |
| AI brain | Claude API (Anthropic SDK) | Categorization, insights, agent |
| Local scripts | Python CLI (`finance.py`) | Heavy parsing, debt planning, reports |
| FX rates | exchangerate-api.com (free) | Daily rate sync |
| Memory | claude-mem | Cross-session project memory |

---

## Budget Framework (Custom — Debt-Heavy Phase)

```
40% → Needs    (rent, food, utilities, transport, health)
30% → Debt Kill (CC minimums + avalanche extra payment)
20% → Savings  (emergency fund first, then goals)
10% → Wants    (dining out, entertainment, shopping)
```

Transition to 50/30/20 (Needs/Wants/Savings) once all high-interest debt is cleared.

---

## Google Sheets Structure (8 Sheets)

### 1. `Income`
`date | source | amount | currency | exchange_rate | amount_inr | type`  
Types: salary / freelance / cashback / refund / other

### 2. `Transactions` (master ledger)
`date | card_account | merchant | amount | currency | exchange_rate | amount_inr | category | subcategory | budget_type | payment_method | notes`  
budget_type: need / want / debt / save / petty

### 3. `Debts`
`debt_name | type | bank | initial_amount | total_outstanding | interest_rate | min_payment | emi_amount | due_date | payoff_priority | avalanche_order`  
Types: CC / gold / personal

### 4. `Budget`
`month | category | budget_type | allocated_inr | spent_inr | variance | pct_used`

### 5. `Goals`
`goal_name | type | target_inr | saved_so_far | target_date | monthly_contribution | months_remaining`  
Types: emergency / travel / investment / tax-saving

### 6. `Net_Worth`
`month | total_assets | total_liabilities | net_worth | mom_change`

### 7. `FX_Rates` (dynamic rows, not hardcoded columns)
`date | currency_code | rate_to_inr`  
Supports any currency — new currency = new row, no schema change.

### 8. `Categories` (master taxonomy — Claude and n8n both reference this)
`category | subcategory | budget_type`

### 9. `Vendor_Map` (self-training categorization)
`vendor_pattern | normalized_name | category | subcategory | confidence | last_seen`  
confidence: auto (AI-inferred) / user (confirmed via Telegram)

---

## Category Taxonomy

### NEEDS
- Housing → Rent, Maintenance, Society charges
- Food & Groceries → Grocery, Pharmacy, Quick commerce (Blinkit/Instamart)
- Transport → Fuel, Cab, Metro, Essential flights
- Utilities → Electricity, Internet, Mobile, Gas
- Health → Doctor, Lab tests, Pharmacy
- Insurance → Life, Health, Vehicle

### WANTS
- Food & Dining → Restaurants, Zomato, Swiggy
- Entertainment → Netflix, Gaming, OTT, Events
- Shopping → Clothes, Lifestyle, Amazon (non-essential)
- Travel → Hotels, Flights (leisure), Klook, experiences
- Personal Care → Salon, Spa, Wellness

### DEBT
- Credit Cards → ICICI Amazon Pay, SBI Card, Scapia Federal, RBL Bank, Card 5
- Gold Loan → Principal + Interest
- Personal Loan → EMI
- EMI Purchases → FlexiPay, Split-n-Pay, BNPL

### SAVINGS
- Emergency Fund → Target: 3–6 months expenses
- Travel Fund → Nomad / global citizen goal
- Investment → SIP, index funds, stocks
- Tax Savings → ELSS, PPF, 80C instruments

### INCOME (tracked separately in Income sheet)
- Salary, Freelance, Cashback, Refund, Other

---

## n8n Workflows (6)

### WF1: Statement Ingestion
Trigger: New MD file uploaded to Google Drive folder  
Flow:
1. Read file content
2. Code node: extract transactions (regex, card-type detection)
3. Deduplication check against Transactions sheet (idempotency)
4. Claude API: categorize each row using Vendor_Map + Categories sheet
5. Confidence < 80% → Telegram inline keyboard: tap to confirm category
6. Write confirmed rows to Transactions sheet
7. Update Vendor_Map with new confirmed vendors
8. Error → WF6 (error handler)

### WF2: AI Telegram Agent
Trigger: Telegram webhook (any message)  
Flow:
1. Claude AI Agent node with memory buffer (conversation persists)
2. Tools available to agent: read Transactions, Budget, Debts, Goals sheets
3. Quick-add: "500 zomato" → parse → confirm → log to Transactions
4. Petty cash: "200 auto petty" → tagged as petty cash type
5. Query: "how much left this week?" → agent reads sheets, responds
6. Voice notes → transcribe → parse → log

### WF3: FX Rate Sync
Trigger: Daily cron 6:00am IST  
Flow:
1. Fetch all active currencies from FX_Rates sheet (distinct currency_code)
2. Call exchangerate-api.com for rates to INR
3. Append new rows to FX_Rates (date + currency + rate)
4. Error → use yesterday's rates + Telegram alert via WF6

### WF4: Daily Summary
Trigger: Daily cron 9:00pm IST  
Flow:
1. Sum today's Transactions by category
2. Calculate: % of weekly budget used per category
3. Flag any category > 80% of weekly allocation
4. Telegram message: today's spend summary + warnings

### WF5: Monthly Report
Trigger: Cron 1st of every month, 8:00am IST  
Flow:
1. Aggregate previous month: income vs spend vs budget (variance)
2. Debt avalanche: current priority card, payment made, balance remaining, progress %
3. Net worth delta: update Net_Worth sheet
4. Goals progress: emergency fund %, travel fund %
5. Top 5 merchants by spend
6. Generate markdown report → upload to Google Drive → Telegram summary

### WF6: Error Handler
Trigger: Error trigger (any workflow failure)  
Flow:
1. Telegram alert: which workflow failed, which step, error message
2. Auto-retry 3x with exponential backoff (1s → 2s → 5s)
3. After 3 failures: store raw payload as dead letter in Drive, alert for manual review

---

## Python CLI: `finance.py`

### Stack
```
pandas        data processing and aggregation
gspread       Google Sheets API read/write
anthropic     Claude API for categorization
click         CLI subcommand routing
python-dotenv credentials management
```

### Commands
```bash
python finance.py parse  --file SBI_Card.md       # parse CC statement → Transactions sheet
python finance.py debt                             # avalanche + snowball hybrid payoff plan
python finance.py worth                            # net worth snapshot → Net_Worth sheet
python finance.py report --month 2026-05           # full monthly report → Drive + Telegram
python finance.py fx     --amount 70.80 --from EUR # single currency conversion
```

### `parse` — CC Statement Parser
Detects card type from MD header, applies card-specific parser:
- **ICICI Amazon Pay**: strips Ser No., handles EMI amortization rows (Interest/Principal/IGST), maps reward points
- **SBI Card**: parses C/D/M suffixes (Credit/Debit/Monthly EMI), separates FlexiPay EMI rows
- **Scapia Federal**: strips Coins column, handles refund rows (+ prefix)
- **RBL Bank**: parses CR suffix, extracts original foreign currency + amount from description
- **Card 5**: parser added once MD format is provided

Output: normalized DataFrame with unified schema → appended to Transactions sheet

### `debt` — Hybrid Avalanche + Snowball
Reads Debts sheet:
- Avalanche order: sort by interest rate DESC (mathematically optimal)
- Quick wins: flag debts < ₹20,000 for fast psychological kills
- Output: month-by-month payoff schedule, total interest saved vs minimum-only payments
- Scenario: "Pay ₹X extra/month → debt-free by [date], saves ₹Y in interest"

### `config.py` — Single source of truth
```python
GOOGLE_SHEETS_ID  = os.getenv("GOOGLE_SHEETS_ID")
CLAUDE_API_KEY    = os.getenv("CLAUDE_API_KEY")
FX_API_KEY        = os.getenv("FX_API_KEY")
BASE_CURRENCY     = "INR"
SALARY_DAY        = 1
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
```

---

## Security Requirements

| Requirement | Implementation |
|---|---|
| Credentials | `.env` file only. Never hardcoded. `.gitignore` from day one. |
| Google Sheets | Service account with least-privilege (read/write target sheet only) |
| Telegram bot | Validate webhook secret token on every n8n request |
| Google Drive | Statement folder set to private. No sharing links. |
| n8n credentials | Stored in n8n encrypted credential vault, not in workflow JSON |
| CC data in MDs | Card numbers already masked in source files ✓ |
| Claude API calls | Send merchant + amount only. Strip full statement text before API call. |
| Git repo | Init with `.gitignore` covering `.env`, `credentials.json`, `*.pdf` |

**Security review:** Run `security-review` skill after each implementation phase.  
**Code review:** Run `code-review` skill after each script is complete.

---

## Data Flow Summary

```
Google Drive (MD files)
        ↓ n8n WF1
        ↓ Claude API categorizes
        ↓
Google Sheets (8 sheets — source of truth)
        ↑ python finance.py (local parsing + planning)
        ↓
Telegram Bot (WF2 agent — all user interaction)
        ↑ you (quick-adds, petty cash, queries)
```

---

## Verification Plan

After each implementation phase:
1. Upload a real CC statement MD → verify rows appear correctly in Transactions sheet
2. Send "500 zomato food" to Telegram → verify logged with correct category
3. Send unknown vendor → verify Telegram inline keyboard appears for confirmation
4. Check FX_Rates sheet is populated after WF3 runs
5. Run `python finance.py debt` → verify avalanche order matches expected interest rates
6. Trigger WF6 manually → verify Telegram error alert fires

---

## Implementation Phases (for writing-plans)

### Phase 0: Setup & Infrastructure
- Git init, .gitignore, .env template
- Google Sheets: create all 8 sheets with correct headers
- Categories sheet: populate full taxonomy
- n8n: connect credentials (Google Drive, Google Sheets, Telegram, Claude API)
- Telegram: create bot via BotFather, get token

### Phase 1: Statement Parser (finance.py parse)
- `config.py` + `fx_convert.py`
- Card-specific parsers for all 4 existing CCs
- Test: parse all 4 existing MD files, verify output schema

### Phase 2: n8n WF1 + WF2 (core workflows)
- WF1: Drive trigger → parse → categorize → Sheets
- WF2: Telegram AI Agent with memory + quick-add
- WF6: Error handler
- Test: end-to-end upload → Telegram confirmation → Sheets

### Phase 3: Automation layer (WF3 + WF4 + WF5)
- WF3: Daily FX sync
- WF4: Daily Telegram summary
- WF5: Monthly report
- Test: trigger each manually, verify outputs

### Phase 4: Debt + Net Worth scripts
- `debt_planner.py` — avalanche + snowball
- `net_worth.py` — monthly snapshot
- Test: run against real debt data, verify payoff schedule math

### Phase 5: Hardening
- Security review (run `security-review` skill)
- Code review (run `code-review` skill)
- Dedup stress test: upload same statement twice → verify no double-logging
- claude-mem: run `/learn-codebase` to front-load full repo into memory

---

## Key n8n Templates to Start From (not reinvent)

- [Automatic expense tracking: Telegram + AI + Google Sheets](https://n8n.io/workflows/6210-automatic-expense-tracking-with-telegram-ai-and-google-sheets/)
- [AI-powered finance manager: Telegram + Google Sheets](https://n8n.io/workflows/7411-ai-powered-personal-finances-manager-with-gemini-telegram-and-google-sheets/)
- [Google Drive PDF → AI → Google Sheets](https://github.com/mativallej/ai-expense-tracker-n8n)
- [Telegram AI Agent chatbot starter](https://n8n.io/workflows/2402-telegram-bot-starter-template-setup-and-ai-agent-chatbot/)
