# onboard-new-month — Monthly Ritual

Run on the **1st of each month**, before WF5 fires at 8am IST. Steps are ordered — do not skip or reorder.

---

## Checklist (run in order)

### Step 1: Parse all CC statements

Download each card's statement from netbanking (export as PDF → convert to MD, or if MD export is available use directly). Save to `statements/` directory.

```bash
python finance.py parse --file statements/ICICI_Bank.md
python finance.py parse --file statements/RBL_Bank.md
python finance.py parse --file statements/SBI_Card.md
python finance.py parse --file statements/Scapia.md
```

**After each parse, verify:**
- Row count in terminal matches expected transaction count for the month.
- Zero duplicate warnings (dedup key: `date + merchant + amount_inr`).
- No `[ERROR]` lines in output.

If a statement file is missing: download it now — do not skip cards. Unparsed cards = blind spots in budget.

---

### Step 2: Log petty cash

Add any cash or UPI expenses not captured by a CC statement.

**CLI:**
```bash
python3 scripts/quick_add.py \
  --merchant "Auto rickshaw" \
  --amount 80 \
  --payment_method cash \
  --notes "Office commute"
```

**Via Telegram (faster for single items):**
```
80 auto petty
```
WF2 parses this as: amount=80, merchant=auto, budget_type=petty.

**When to use `budget_type=petty`:** Small cash spends (< ₹200) where exact category tracking adds no value. These appear in total spend but not in the 4-bucket percentage.

---

### Step 3: Log income

Add salary and any freelance/other income to the `Income` sheet manually (no CLI command yet):

| date | source | amount | currency | exchange_rate | amount_inr | type |
|---|---|---|---|---|---|---|
| 2026-06-01 | Employer | 85000 | INR | 1.0 | 85000 | salary |
| 2026-06-01 | Freelance Client | 500 | USD | 84.2 | 42100 | freelance |

For foreign income: look up rate from `FX_Rates` sheet for that date, or run:
```bash
python finance.py fx --amount 500 --from USD
```

---

### Step 4: Sync FX rates

Ensure current month's rates are stored before budget calculations:

```bash
python3 scripts/sync_fx.py
```

This writes today's rates to `FX_Rates` sheet as `(date, currency_code, rate_to_inr)`. WF3 does this daily at 6am IST, but run manually to be safe if you're doing this early morning before WF3 fires.

---

### Step 5: Budget check

```bash
python3 scripts/query_budget.py --month YYYY-MM
```

Replace `YYYY-MM` with the **month just ended** (e.g., `2026-05` if running on June 1st).

**Targets:**

| Bucket | Target |
|---|---|
| 🏠 Needs | < 40% |
| 💳 Debt | ≥ 30% |
| 💰 Savings | ≥ 20% |
| 🎯 Wants | < 10% |

If any bucket is off: check top categories in that bucket via `python finance.py report --month YYYY-MM`. Note variance in `Budget` sheet `notes` column if justified (one-off expense).

---

### Step 6: Update net worth

```bash
python finance.py worth
```

When prompted, enter:
- Current salary account balance (check bank app)
- Investment values (Zerodha/mutual fund app → current portfolio value)
- Any other liquid assets

This writes a new row to `Net_Worth` sheet with today's date and computed net worth (assets − liabilities from Debts sheet).

---

### Step 7: Verify monthly report (WF5)

WF5 auto-runs at **8am IST on the 1st**. Check Telegram for the monthly report message.

The report includes:
- Budget actuals vs targets
- Goals progress
- Net worth change MoM
- Debt remaining + projected payoff date

**If the report is missing:** Trigger WF5 manually in n8n dashboard → find "WF5 Monthly Report" → click "Execute Workflow".

---

### Step 8: Debt avalanche review

```bash
python finance.py debt
```

Check:
- The highest-interest card is listed first (avalanche priority).
- Minimum payments on all other cards are logged.
- Is there a **quick win** — any card balance < ₹20,000? If so, consider wiping it this month to eliminate one payment.

After any payoff: update the `Debts` sheet — set `outstanding_balance` to 0, add `closed_date`.

---

### Step 9: Security review (quarterly)

Run every 3 months (March, June, September, December):

```
.claude/skills/security-review.md
```

Covers: API key rotation, service account permissions audit, Telegram webhook secret check, `.env` / `credentials.json` gitignore verification.

---

## Completion Criteria

All 8 steps (9 quarterly) done when:
- [ ] `Transactions` sheet has no blank `category` rows for the closed month
- [ ] `Income` sheet has all income sources for the closed month
- [ ] `query_budget.py` shows expected split with no errors
- [ ] `Net_Worth` sheet has a new row dated today
- [ ] WF5 Telegram report received (or manually triggered)
- [ ] Debt avalanche list reviewed; any quick win actioned or noted

**Time estimate:** 20–30 minutes if statements are ready. Bottleneck is usually downloading PDFs.
