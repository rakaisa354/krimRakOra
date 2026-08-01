# budget-check — Read and Act on Budget Data

---

## CLI Usage

```bash
# Current month
python3 scripts/query_budget.py

# Specific month
python3 scripts/query_budget.py --month 2026-05
```

`query_budget.py` reads all rows from the `Transactions` sheet where `date` starts with the target month and `amount_inr > 0` (excludes credits/refunds). Groups by `budget_type` and `category`.

---

## Output Format

```
📊 *2026-06 Spending Summary*
Total: ₹85,420

🏠 Needs: ₹32,400 (38%)
🎯 Wants: ₹7,200 (8%)
💳 Debt: ₹26,000 (30%)
💰 Savings: ₹17,100 (20%)

*Top categories:*
  Rent: ₹18,000
  Groceries: ₹6,200
  EMI - RBL: ₹14,000
  Food Delivery: ₹4,100
  Utilities: ₹3,800

_47 transactions_
```

---

## Budget Types Mapping

| `budget_type` value | Display label | Target % |
|---|---|---|
| `need` | 🏠 Needs | ≤ 40% |
| `want` | 🎯 Wants | ≤ 10% |
| `debt` | 💳 Debt | ≥ 30% |
| `save` | 💰 Savings | ≥ 20% |
| `petty` | Petty cash | Not counted in main budget % |

`petty` transactions are included in the total spend but excluded from the 4-bucket percentage calculation. Use `petty` for small cash spends (auto rickshaw, chai, etc.) that don't warrant tracking.

---

## Interpreting Results

### Healthy state
```
Needs  < 40%   ✓
Wants  < 10%   ✓
Debt   ≥ 30%   ✓  (aggressive payoff)
Savings ≥ 20%  ✓
```

### Red flags

| Signal | What it means | Action |
|---|---|---|
| Wants > 15% | Lifestyle creep | Check top want categories; cut or reallocate |
| Debt < 25% | Underpaying debt | Review debt transactions — was EMI skipped? |
| Savings = 0% | Emergency | Investigate — was salary deposited? Any large one-off need? |
| Needs > 50% | Structural cost spike | Check rent, utilities — or large medical/repair cost |

---

## Weekly Budget Calculation

```
weekly_budget = monthly_allocation / 4.33
```

4.33 = average weeks per month (52 weeks ÷ 12 months). Use this to sanity-check mid-month pace:

```python
# Example: monthly needs budget = ₹40,000
# Week 2 of month → expected spend ≤ 40000 / 4.33 * 2 ≈ ₹18,475
```

---

## When a Category Hits 80%

WF4 sends a Telegram alert automatically at 9pm IST when any bucket reaches 80% of allocation. If you get that alert:

1. **Identify the culprit:**
   ```bash
   python finance.py report --month YYYY-MM
   ```
   Look at the top merchants in the flagged category.

2. **Decide:**
   - Cut spending for the rest of the month (preferred).
   - Or reallocate from a healthier bucket.

3. **If reallocating:**
   - Open `Budget` sheet.
   - Find the row for the current month.
   - Reduce `allocated_inr` for the donor category; increase for the recipient.
   - `query_budget.py` recalculates percentages against the updated allocations on next run.

---

## Month-End Review Checklist

Run this on the last day of the month (or 1st before WF5 fires):

- [ ] **All CC statements parsed** — `python finance.py parse --file` for each card
- [ ] **Petty cash added** — any cash/UPI spends not on a CC via `quick_add.py` or Telegram
- [ ] **query_budget shows expected split** — Needs <40%, Debt ≥30%, Savings ≥20%, Wants <10%
- [ ] **Variance < 10% per category** — if over, write a one-line note in the Budget sheet `notes` column explaining why (e.g., "dental bill 8k")
- [ ] **No uncategorized rows** — filter `Transactions` sheet where `category` is blank; fix manually or re-run categorizer

---

## Verification

```bash
python3 scripts/query_budget.py --month 2026-06
```

Expected: output prints without error, shows 4 budget buckets, total > 0.

If total shows ₹0 for a month you know has transactions: check that `date` column in `Transactions` sheet uses `YYYY-MM-DD` format (not DD/MM/YYYY).
