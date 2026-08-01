# n8n WF3 — FX Rate Sync

**Job:** Fetch daily exchange rates from exchangerate-api.com at 6:00am IST, compute `rate_to_inr` for 8 currencies, append to the `FX_Rates` sheet. Fall back to yesterday's rates if the API fails.

---

## Credentials Required

| Credential Name (n8n vault) | Type | Used by |
|---|---|---|
| `FX API Key` | stored as n8n env or credential | HTTP Request URL |
| `Google Sheets OAuth` | OAuth2 | Sheets Append + Read nodes |
| `Telegram Bot` | Telegram API | Error alert node |

---

## Schedule

| Setting | Value |
|---|---|
| Cron expression | `30 0 * * *` |
| Meaning | 00:30 UTC = 06:00 IST daily |
| Timezone in n8n | Set workflow timezone to `Asia/Kolkata` OR use UTC cron above |

---

## Currencies to Sync

`USD`, `GBP`, `EUR`, `SGD`, `AED`, `THB`, `MYR`, `JPY`

---

## Node Map

```
[Cron Trigger]
      ↓
[HTTP GET — FX API]
      ├─ success → [Code: Parse & Compute] → [Sheets Append: FX_Rates]
      └─ error   → [Sheets Read: Last Row per Currency] → [Telegram: FX Sync Failed Alert] → WF6
```

---

## Node 1 — Cron Trigger

| Field | Value |
|---|---|
| Node type | `n8n-nodes-base.scheduleTrigger` |
| Rule | Cron Expression: `30 0 * * *` |

---

## Node 2 — HTTP GET FX API

| Field | Value |
|---|---|
| Node type | `n8n-nodes-base.httpRequest` |
| Method | `GET` |
| URL | `https://v6.exchangerate-api.com/v6/{{ $env.FX_API_KEY }}/latest/INR` |
| Response format | JSON |
| On error | Continue (connect error output to fallback branch) |

The API returns rates where `INR = 1` (base). So `conversion_rates.USD = 0.012` means 1 INR = 0.012 USD. To get `rate_to_inr` (how many INR per 1 foreign unit): `1 / conversion_rates.USD`.

---

## Node 3 — Code: Parse & Compute Rates

```js
const rates = $input.first().json.conversion_rates;
const today = new Date().toISOString().split('T')[0];
const currencies = ['USD', 'GBP', 'EUR', 'SGD', 'AED', 'THB', 'MYR', 'JPY'];

const rows = currencies.map(code => ({
  json: {
    date: today,
    currency_code: code,
    rate_to_inr: parseFloat((1 / rates[code]).toFixed(4))
  }
}));

return rows;
```

Output: one item per currency, each with `{ date, currency_code, rate_to_inr }`.

---

## Node 4 — Google Sheets Append: FX_Rates

| Field | Value |
|---|---|
| Node type | `n8n-nodes-base.googleSheets` |
| Operation | `appendOrUpdate` |
| Sheet | `FX_Rates` |
| Columns | `date`, `currency_code`, `rate_to_inr` |
| Map fields | date → `date`, currency_code → `currency_code`, rate_to_inr → `rate_to_inr` |

FX_Rates tab column order: `A=date | B=currency_code | C=rate_to_inr`

---

## Error Branch — Fallback to Yesterday's Rates

### Node 5a — Sheets Read: Last Rates

Triggered from Node 2's **error output**.

| Field | Value |
|---|---|
| Operation | `getAll` |
| Sheet | `FX_Rates` |
| Filters | None — read all, filter in Code node |

### Node 5b — Code: Get Yesterday's Rates

```js
const allRows = $input.all().map(i => i.json);
const currencies = ['USD', 'GBP', 'EUR', 'SGD', 'AED', 'THB', 'MYR', 'JPY'];
const today = new Date().toISOString().split('T')[0];

// Get most recent row per currency
const latest = {};
allRows.forEach(row => {
  const c = row.currency_code;
  if (!latest[c] || row.date > latest[c].date) latest[c] = row;
});

// Re-stamp with today's date (carry forward)
const rows = currencies.map(code => ({
  json: {
    date: today,
    currency_code: code,
    rate_to_inr: latest[code] ? parseFloat(latest[code].rate_to_inr) : null,
    source: 'carried_forward'
  }
}));
return rows;
```

Then connect to the same **Sheets Append** node (Node 4).

### Node 5c — Telegram Alert

```
⚠ FX sync failed — using yesterday's rates
Date: {{ new Date().toISOString().split('T')[0] }}
Check: https://v6.exchangerate-api.com status
```

Connect error output of Node 5c → **WF6**.

---

## Verification

1. Trigger WF3 manually (n8n → Execute Workflow).
2. Open **FX_Rates** sheet — 8 new rows with today's date should appear.
3. Spot-check: Google "1 USD to INR" — `rate_to_inr` for USD should be within ±1 of market rate.
4. Test error path: temporarily set an invalid API key → verify carried-forward rows appear + Telegram alert fires.
5. Check n8n execution log — all nodes green (or error branch handled cleanly).
