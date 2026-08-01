# goal-track — Manage and Update Financial Goals

---

## Goals Sheet Schema

Sheet tab: `Goals`

| Col | Field | Type | Description |
|---|---|---|---|
| A | `goal_name` | STRING | Unique identifier (e.g., "Emergency Fund") |
| B | `type` | STRING | `emergency` / `travel` / `investment` / `tax-saving` |
| C | `target_inr` | FLOAT | Total amount to reach |
| D | `saved_so_far` | FLOAT | Running total saved |
| E | `target_date` | DATE | `YYYY-MM-DD` deadline |
| F | `monthly_contribution` | FLOAT | INR allocated per month toward this goal |
| G | `months_remaining` | FLOAT | Auto-calculated: `(target - saved) / monthly_contribution` |

---

## Goal Types & Priority Order (Debt-Kill Phase)

During debt-kill phase, savings allocation (20%) is split across goals in this order:

| Priority | Goal Type | Notes |
|---|---|---|
| 1 | `emergency` | Non-negotiable first. Target = `avg_monthly_spend × 3` |
| 2 | Debt payoff | Not a Goals row — tracked in Debts sheet, takes 30% budget |
| 3 | `travel` | Nomad/global citizen fund — fund only after emergency is ≥50% |
| 4 | `investment` | Long-term wealth building |
| 4 | `tax-saving` | ELSS/PPF — time-sensitive (March deadline) |

**Emergency fund target calculation:**
```python
# Pull last 3 months from Transactions sheet
# avg_monthly_spend = sum of all amount_inr (budget_type != 'debt') / 3 months
# emergency_target = avg_monthly_spend * 3
```
Run this manually or use `python finance.py report` output to get avg monthly spend.

---

## How to Update `saved_so_far`

### Option A: Direct sheet edit
Open `Goals` sheet → find goal row → edit `saved_so_far` cell → manually recalculate `months_remaining`.

### Option B: Script (recommended for precision)

```python
# scripts/update_goal.py (create as needed)
from sheets import get_sheet, read_all

def add_to_goal(goal_name: str, amount: float):
    sheet = get_sheet('Goals')
    goals = read_all('Goals')
    match = next((i for i, g in enumerate(goals) if g['goal_name'] == goal_name), None)
    if match is None:
        raise ValueError(f'Goal not found: {goal_name}')
    current = float(goals[match]['saved_so_far'])
    new_total = current + amount
    row_num = match + 2  # 1-indexed + header row
    sheet.update_cell(row_num, 4, new_total)  # col 4 = saved_so_far
    # recalculate months_remaining
    target = float(goals[match]['target_inr'])
    monthly = float(goals[match]['monthly_contribution'])
    remaining = max(0, (target - new_total) / monthly) if monthly else 0
    sheet.update_cell(row_num, 7, round(remaining, 1))  # col 7 = months_remaining
    print(f'✓ {goal_name}: ₹{new_total:,.0f} / ₹{target:,.0f} ({new_total/target*100:.0f}%)')
```

**Usage:**
```bash
python3 -c "
import sys, os; sys.path.insert(0, '.')
from scripts.update_goal import add_to_goal
add_to_goal('Emergency Fund', 5000)
"
```

---

## Telegram Query

User sends natural language to WF2 agent:
```
"emergency fund progress"
"how far am I from travel goal"
"goals summary"
```

WF2 reads the `Goals` sheet via `read_all('Goals')` and responds with:
- Goal name, percentage complete, months remaining
- Whether on track vs behind (compare `months_remaining` to months until `target_date`)

**On-track check:**
```python
from datetime import date
from dateutil.relativedelta import relativedelta

months_to_deadline = relativedelta(target_date, date.today()).months + relativedelta(target_date, date.today()).years * 12
on_track = months_remaining <= months_to_deadline
```

---

## Monthly Goal Review

WF5 (monthly report, 8am on 1st) includes a goals section. Check:

1. Is any goal **behind**? (`months_remaining > months_to_deadline`)
   - If yes: either increase `monthly_contribution` (reduce another goal's contribution) or push `target_date` out.

2. Is an **emergency fund** goal not yet at 100%? → It gets first claim on Savings allocation.

3. Is any goal **completed**? (`saved_so_far >= target_inr`)
   - Archive it: add a `completed_date` note in an unused column, remove from active goals.
   - Redirect its `monthly_contribution` to the next priority goal.

4. **Tax-saving goals**: check if it's Q3/Q4 (Oct–Mar) — front-load contributions if needed to hit ₹1.5L ELSS limit by March 31.

---

## Verification

After calling `add_to_goal()`:

1. Open `Goals` sheet.
2. Confirm `saved_so_far` increased by the exact amount passed.
3. Confirm `months_remaining` decreased accordingly.
4. Run Telegram query "goals summary" → WF2 should reflect updated numbers.
