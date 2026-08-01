# n8n WF5 — Monthly Financial Report

**Job:** On the 1st of each month at 8am IST, compile last month's full financial report — income vs spend, debt avalanche progress, net worth delta, goals — upload to Drive, send a Telegram summary with the link.

---

## Credentials Required

| Credential Name (n8n vault) | Type | Used by |
|---|---|---|
| `Google Sheets OAuth` | OAuth2 | All Sheets read nodes |
| `Google Drive OAuth` | OAuth2 | Drive upload node |
| `Telegram Bot` | Telegram API | Summary message |

---

## Schedule

| Setting | Value |
|---|---|
| Cron expression | `30 2 1 * *` |
| Meaning | 02:30 UTC = 08:00 IST, 1st of every month |

---

## Node Map

```
[Cron Trigger]
      ↓
[Code: Determine Report Month]
      ↓
[Sheets Read: Transactions] ──┐
[Sheets Read: Income]         ├─→ [Code: Build Report]
[Sheets Read: Debts]          │         ↓
[Sheets Read: Goals]          │   [Drive: Upload Report.md]
[Sheets Read: Net_Worth] ─────┘         ↓
                                  [Telegram: Monthly Summary]
```

> All 5 Sheets reads can run in parallel — connect Cron Trigger to all 5 simultaneously, then merge into the Code node using a **Merge** node (mode: `Combine`, merge by position disabled — just pass all items).

---

## Node 1 — Cron Trigger

Cron: `30 2 1 * *`

---

## Node 2 — Code: Determine Report Month

Run this immediately after trigger to set context for all downstream nodes.

```js
const now = new Date();
const reportDate = new Date(now.getFullYear(), now.getMonth() - 1, 1);
const reportMonth = reportDate.toISOString().slice(0, 7); // "2026-05"
const reportLabel = reportDate.toLocaleString('en-IN', { month: 'long', year: 'numeric' }); // "May 2026"

return [{ json: { reportMonth, reportLabel } }];
```

---

## Nodes 3–7 — Google Sheets Reads (all parallel)

| Node | Sheet | Filter in Code |
|---|---|---|
| Sheets Read: Transactions | `Transactions` | `date.startsWith(reportMonth)` |
| Sheets Read: Income | `Income` | `month === reportMonth` |
| Sheets Read: Debts | `Debts` | All rows (current state) |
| Sheets Read: Goals | `Goals` | All rows (current state) |
| Sheets Read: Net_Worth | `Net_Worth` | Last 2 rows (this month + prev) |

All use `getAll` operation.

---

## Node 8 — Code: Build Report

```js
const reportMonth = $('Code: Determine Report Month').first().json.reportMonth;
const reportLabel = $('Code: Determine Report Month').first().json.reportLabel;

// --- Transactions ---
const txns = $('Sheets Read: Transactions').all()
  .map(i => i.json)
  .filter(t => t.date && t.date.startsWith(reportMonth) && parseFloat(t.amount_inr) > 0);

const totalSpend = txns.reduce((s, t) => s + parseFloat(t.amount_inr), 0);

const byType = {};
txns.forEach(t => {
  const type = t.budget_type || 'other';
  byType[type] = (byType[type] || 0) + parseFloat(t.amount_inr);
});

// Top 5 merchants
const merchantTotals = {};
txns.forEach(t => {
  merchantTotals[t.merchant] = (merchantTotals[t.merchant] || 0) + parseFloat(t.amount_inr);
});
const top5 = Object.entries(merchantTotals)
  .sort((a, b) => b[1] - a[1])
  .slice(0, 5);

// --- Income ---
const incomeRows = $('Sheets Read: Income').all().map(i => i.json)
  .filter(r => r.month === reportMonth);
const totalIncome = incomeRows.reduce((s, r) => s + parseFloat(r.amount_inr || 0), 0);
const saved = totalIncome - totalSpend;

// --- Debts ---
const debts = $('Sheets Read: Debts').all().map(i => i.json);
const priorityDebt = debts.sort((a, b) => parseFloat(b.interest_rate) - parseFloat(a.interest_rate))[0];
const debtPaid = byType['debt'] || 0;

// --- Net Worth ---
const nwRows = $('Sheets Read: Net_Worth').all().map(i => i.json)
  .sort((a, b) => b.date > a.date ? 1 : -1);
const netWorthNow = parseFloat(nwRows[0]?.net_worth_inr || 0);
const netWorthPrev = parseFloat(nwRows[1]?.net_worth_inr || 0);
const nwDelta = netWorthNow - netWorthPrev;

// --- Goals ---
const goals = $('Sheets Read: Goals').all().map(i => i.json).map(g => ({
  name: g.goal_name,
  pct: Math.round((parseFloat(g.saved_inr) / parseFloat(g.target_inr)) * 100)
}));

// --- Build markdown report ---
const top5Lines = top5.map(([m, amt]) => `  - ${m}: ₹${amt.toFixed(0)}`).join('\n');
const goalLines = goals.map(g => `  - ${g.name}: ${g.pct}%`).join('\n');
const typeBreakdown = Object.entries(byType)
  .map(([t, v]) => `  - ${t}: ₹${v.toFixed(0)}`).join('\n');

const report = `# krimRakOra — ${reportLabel} Report

## Summary
- Income: ₹${totalIncome.toFixed(0)}
- Total Spend: ₹${totalSpend.toFixed(0)}
- Net Saved: ₹${saved.toFixed(0)}

## Spend by Budget Type
${typeBreakdown}

## Top 5 Merchants
${top5Lines}

## Debt Avalanche
- Priority card: ${priorityDebt?.account_name || 'N/A'} @ ${priorityDebt?.interest_rate || 'N/A'}%
- This month's payment: ₹${debtPaid.toFixed(0)}
- Balance remaining: ₹${parseFloat(priorityDebt?.balance_inr || 0).toFixed(0)}
- % paid off: ${priorityDebt ? Math.round((1 - priorityDebt.balance_inr / priorityDebt.original_inr) * 100) : 0}%

## Net Worth
- This month: ₹${netWorthNow.toFixed(0)}
- MoM delta: ${nwDelta >= 0 ? '+' : ''}₹${nwDelta.toFixed(0)}

## Goals Progress
${goalLines}
`;

const telegramSummary = `📅 ${reportLabel} Report
Income: ₹${totalIncome.toFixed(0)} | Spent: ₹${totalSpend.toFixed(0)} | Saved: ₹${saved.toFixed(0)}
Debt paid: ₹${debtPaid.toFixed(0)} | Priority: ${priorityDebt?.account_name || 'N/A'} @ ${priorityDebt?.interest_rate || 'N/A'}%
Net worth: ₹${netWorthNow.toFixed(0)} (${nwDelta >= 0 ? '+' : ''}₹${nwDelta.toFixed(0)} MoM)`;

return [{
  json: {
    report,
    telegramSummary,
    filename: `Report_${reportMonth}.md`,
    reportMonth
  }
}];
```

---

## Node 9 — Google Drive: Upload Report

| Field | Value |
|---|---|
| Node type | `n8n-nodes-base.googleDrive` |
| Operation | `upload` |
| File name | `={{ $json.filename }}` |
| File content | `={{ $json.report }}` |
| MIME type | `text/markdown` |
| Parent folder | Drive folder ID for `reports/` |

Output: `$json.id` (Drive file ID), `$json.webViewLink` (shareable URL).

---

## Node 10 — Telegram: Monthly Summary

```
{{ $('Code: Build Report').first().json.telegramSummary }}
Full report: {{ $json.webViewLink }}
```

---

## Verification

1. Manually trigger WF5 (ensure last month has ≥1 transaction row).
2. Check **Google Drive** `reports/` folder — `Report_YYYY-MM.md` should exist.
3. Open file — verify all sections populated (no NaN or undefined).
4. Check **Telegram** — summary message with Drive link should arrive.
5. Click Drive link — report should open and be readable.
6. Edge case: trigger on a month with no transactions → report shows ₹0 spend, no top merchants.
