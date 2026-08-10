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
[Sheets Read: Transactions]
      ↓
[Sheets Read: Income]
      ↓
[Sheets Read: Debts]
      ↓
[Sheets Read: Goals]
      ↓
[Sheets Read: Net_Worth]
      ↓
[Code: Build Report]
      ↓
[Drive: Upload Report.md]
      ↓
[Telegram: Monthly Summary]
```

> **Correction (caught before build):** an earlier draft of this runbook fanned all 5 Sheets
> Read nodes in parallel directly into `Code: Build Report`'s single input, with no Merge node,
> reasoning that "nothing is chained after a multi-item node so there's no race." That reasoning
> was wrong — in n8n, a node with **multiple incoming connections** fires as soon as the FIRST
> predecessor completes, not after all of them, regardless of whether any single predecessor
> emits multiple items. That is the exact bug WF4 hit (`Sheets Read: Budget hasn't been
> executed`), and a 5-way parallel fan-in reproduces it, not avoids it.
>
> The proven fix (WF4's actual resolution) is **sequential chaining, not a Merge node**: each
> Sheets Read node feeds directly into the next, and `Code: Build Report` sits at the end of the
> chain referencing every prior read via `$('Sheets Read: ...')`. Because a chained node
> re-executes once per incoming item by default (WF4's second bug — the "5x-inflation" case),
> set `executeOnce: true` on **every** Sheets Read node in the chain except the first
> (`Transactions`, whose only parent — `Code: Determine Report Month` — always emits exactly one
> item, so no multiplication risk exists there) — and on `Code: Build Report` itself, since its
> immediate parent (`Sheets Read: Net_Worth`) can emit more than one row. Also set
> `alwaysOutputData: true` on all 5 Sheets Read nodes so an empty Debts/Goals/Net_Worth sheet
> doesn't silently halt the whole chain (same class of bug WF4 hit with an empty Budget sheet).

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
| Sheets Read: Income | `Income` | `date.startsWith(reportMonth)` (Income has no `month` column — only `date`) |
| Sheets Read: Debts | `Debts` | All rows (current state) |
| Sheets Read: Goals | `Goals` | All rows (current state) |
| Sheets Read: Net_Worth | `Net_Worth` | Last 2 rows by `month` (this month + prev) — Net_Worth has no `date` column, only `month` |

All use `getAll` operation, chained **sequentially** (Transactions → Income → Debts → Goals →
Net_Worth), per the corrected topology above. `alwaysOutputData: true` on all 5.
`executeOnce: true` on Income, Debts, Goals, and Net_Worth (not Transactions — see correction
note above). `Code: Build Report` also needs `executeOnce: true` since it's chained directly
after Net_Worth.

**Actual column names, verified against `scripts/setup_sheets.py` (source of truth) — the Code
node below must use these exactly, not the plausible-looking names an earlier draft used:**

| Sheet | Actual columns used by Node 8 |
|---|---|
| Income | `date`, `amount_inr` (no `month` field) |
| Debts | `debt_name`, `total_outstanding`, `initial_amount`, `interest_rate` (no `account_name`, `balance_inr`, `original_inr`) |
| Goals | `goal_name`, `saved_so_far`, `target_inr` (no `saved_inr`) |
| Net_Worth | `month`, `net_worth` (no `date`, no `net_worth_inr`) |
| Transactions | `date`, `amount_inr`, `budget_type`, `merchant` — unchanged, already correct |

---

## Node 8 — Code: Build Report

```js
const reportMonth = $('Code: Determine Report Month').first().json.reportMonth;
const reportLabel = $('Code: Determine Report Month').first().json.reportLabel;

// --- Transactions ---
// Do NOT filter to amount_inr > 0 — real statements contain charge/reversal/remainder
// triplets (a purchase immediately reversed, then re-charged as the true net amount, same
// pattern documented in CLAUDE.md for Kotak/ICICI EMI conversions). Filtering out negatives
// double-counts every reversed charge as real spend instead of netting it out. Verified
// against a real July 2026 dataset: summing ALL amount_inr (no sign filter) gives -32564.71,
// matching independent hand-verification; the amount_inr > 0 filter gave a wrong +66516.
const txns = $('Sheets Read: Transactions').all()
  .map(i => i.json)
  .filter(t => t.date && t.date.startsWith(reportMonth));

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

// --- Income --- (Income sheet has no `month` column, only `date`)
const incomeRows = $('Sheets Read: Income').all().map(i => i.json)
  .filter(r => r.date && r.date.startsWith(reportMonth));
const totalIncome = incomeRows.reduce((s, r) => s + parseFloat(r.amount_inr || 0), 0);
const saved = totalIncome - totalSpend;

// --- Debts --- (actual columns: debt_name, total_outstanding, initial_amount)
// Filter out blank rows (a sheet with no real data can still return a truthy {} row from
// getAll, which broke % paid off with NaN — verified against a real test run 2026-08-09)
const debts = $('Sheets Read: Debts').all().map(i => i.json).filter(d => d.debt_name);
const priorityDebt = debts.sort((a, b) => parseFloat(b.interest_rate) - parseFloat(a.interest_rate))[0];
const debtPaid = byType['debt'] || 0;

// --- Net Worth --- (actual columns: month, net_worth — no `date`, no `net_worth_inr`)
const nwRows = $('Sheets Read: Net_Worth').all().map(i => i.json)
  .sort((a, b) => b.month > a.month ? 1 : -1);
const netWorthNow = parseFloat(nwRows[0]?.net_worth || 0);
const netWorthPrev = parseFloat(nwRows[1]?.net_worth || 0);
const nwDelta = netWorthNow - netWorthPrev;

// --- Goals --- (actual column: saved_so_far, not saved_inr)
// Same blank-row guard as Debts — filter before mapping so an empty sheet doesn't produce
// an "undefined: NaN%" line (verified against a real test run 2026-08-09).
const goals = $('Sheets Read: Goals').all().map(i => i.json).filter(g => g.goal_name).map(g => ({
  name: g.goal_name,
  pct: Math.round((parseFloat(g.saved_so_far) / parseFloat(g.target_inr)) * 100)
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
- Net Cash Flow: ₹${saved.toFixed(0)}

## Spend by Budget Type
${typeBreakdown}

## Top 5 Merchants
${top5Lines}

## Debt Avalanche
- Priority card: ${priorityDebt?.debt_name || 'N/A'} @ ${priorityDebt?.interest_rate || 'N/A'}%
- This month's payment: ₹${debtPaid.toFixed(0)}
- Balance remaining: ₹${parseFloat(priorityDebt?.total_outstanding || 0).toFixed(0)}
- % paid off: ${priorityDebt ? Math.round((1 - priorityDebt.total_outstanding / priorityDebt.initial_amount) * 100) : 0}%

## Net Worth
- This month: ₹${netWorthNow.toFixed(0)}
- MoM delta: ${nwDelta >= 0 ? '+' : ''}₹${nwDelta.toFixed(0)}

## Goals Progress
${goalLines}
`;

const telegramSummary = `📅 ${reportLabel} Report
Income: ₹${totalIncome.toFixed(0)} | Spent: ₹${totalSpend.toFixed(0)} | Net cash flow: ₹${saved.toFixed(0)}
Debt paid: ₹${debtPaid.toFixed(0)} | Priority: ${priorityDebt?.debt_name || 'N/A'} @ ${priorityDebt?.interest_rate || 'N/A'}%
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
