# n8n WF4 — Daily Spending Summary

**Job:** Every evening at 9pm IST, pull today's transactions and monthly budget allocations, aggregate by budget type, flag over-80% categories, and send a Telegram digest.

---

## Credentials Required

| Credential Name (n8n vault) | Type | Used by |
|---|---|---|
| `Google Sheets OAuth` | OAuth2 | Transactions + Budget read |
| `Telegram Bot` | Telegram API | Send Message node |

---

## Schedule

| Setting | Value |
|---|---|
| Cron expression | `30 15 * * *` |
| Meaning | 15:30 UTC = 21:00 IST daily |

---

## Node Map

```
[Cron Trigger]
      ↓
[Sheets Read: Transactions]
      ↓
[Sheets Read: Budget]
      ↓
[Code: Aggregate + Flag]
      ↓
[Switch: has_transactions?]
   ├─ yes → [Telegram: Daily Summary]
   └─ no  → [Telegram: No Spend]
```

---

## Node 1 — Cron Trigger

Cron: `30 15 * * *`

---

## Node 2 — Sheets Read: Transactions

| Field | Value |
|---|---|
| Operation | `getAll` |
| Sheet | `Transactions` |
| Fields | All columns (date, merchant, amount_inr, budget_type, category) |

Returns all rows — filtering by today happens in the Code node.

---

## Node 3 — Sheets Read: Budget

| Field | Value |
|---|---|
| Operation | `getAll` |
| Sheet | `Budget` |
| Fields | All columns (month, budget_type, allocated_inr) |

---

## Node 4 — Code: Aggregate & Flag

```js
const today = new Date().toISOString().split('T')[0];
const currentMonth = today.slice(0, 7); // "2026-06"

// --- Transactions: filter today ---
const allTxns = $('Sheets Read: Transactions').all().map(i => i.json);
const txns = allTxns.filter(t =>
  t.date === today && parseFloat(t.amount_inr) > 0
);

// Aggregate by budget_type
const byType = {};
txns.forEach(t => {
  const type = t.budget_type || 'uncategorized';
  byType[type] = (byType[type] || 0) + parseFloat(t.amount_inr);
});

const total = Object.values(byType).reduce((a, b) => a + b, 0);

// --- Budget: filter current month ---
const budgetRows = $('Sheets Read: Budget').all().map(i => i.json);
const monthBudget = {};
budgetRows
  .filter(b => b.month === currentMonth)
  .forEach(b => { monthBudget[b.budget_type] = parseFloat(b.allocated_inr); });

// Weekly allocation = monthly / 4
const warnings = [];
Object.entries(byType).forEach(([type, spent]) => {
  const monthly = monthBudget[type];
  if (!monthly) return;
  const weekly = monthly / 4;
  const pct = Math.round((spent / weekly) * 100);
  if (pct >= 80) {
    warnings.push(`⚠ ${type} is at ${pct}% of weekly budget`);
  }
});

return [{
  json: {
    today,
    total: total.toFixed(0),
    needs: (byType['needs'] || 0).toFixed(0),
    wants: (byType['wants'] || 0).toFixed(0),
    debt: (byType['debt'] || 0).toFixed(0),
    savings: (byType['savings'] || 0).toFixed(0),
    petty: (byType['petty'] || 0).toFixed(0),
    warnings: warnings.join('\n'),
    has_transactions: txns.length > 0,
    txn_count: txns.length
  }
}];
```

---

## Node 5 — Switch: Has Transactions?

| Field | Value |
|---|---|
| Value | `={{ $json.has_transactions }}` |
| Rule 0 | equals `true` → output 0 |
| Fallback | output 1 (no transactions) |

---

## Node 6 — Telegram: Daily Summary

**Chat ID:** Your personal Telegram chat ID.

**Text** (use n8n expression):

```
📊 Today — {{ $json.today }}
Total spent: ₹{{ $json.total }}

🏠 Needs: ₹{{ $json.needs }}
🎯 Wants: ₹{{ $json.wants }}
💳 Debt: ₹{{ $json.debt }}
💰 Savings: ₹{{ $json.savings }}
🪙 Petty: ₹{{ $json.petty }}
{{ $json.warnings ? '\n' + $json.warnings : '' }}
```

---

## Node 7 — Telegram: No Spend

```
✓ No spending logged today
```

---

## Budget Type Reference

| budget_type | Monthly target |
|---|---|
| `needs` | 40% of income |
| `debt` | 30% of income |
| `savings` | 20% of income |
| `wants` | 10% of income |
| `petty` | tracked separately |

---

## Verification

1. Add a test transaction row to Transactions sheet with today's date and budget_type=`needs`, amount_inr=500.
2. Trigger WF4 manually.
3. Telegram message should show `Needs: ₹500` and `Total: ₹500`.
4. If spent > 80% of weekly needs budget → warning line appears.
5. Delete test row; trigger again → `✓ No spending logged today`.
6. Check n8n execution log — Code node output should have `has_transactions: true/false`.
