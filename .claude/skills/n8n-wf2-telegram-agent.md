# n8n WF2 — Telegram AI Agent

**Job:** Receive Telegram messages → classify intent via Claude → either quick-add an expense (GitHub Actions) or answer finance queries (Claude + Sheets).

This is the primary user-facing interface for krimRakOra.

---

## Credentials Required

| Credential Name (n8n vault) | Type | Used by |
|---|---|---|
| `Telegram Bot` | Telegram API | Trigger + Send nodes |
| `Claude API` | HTTP Header Auth (`x-api-key`) | Intent detection node |
| `GitHub PAT` | HTTP Header Auth | Quick-add dispatch |
| `Google Sheets OAuth` | OAuth2 | Sheets read nodes |

---

## Node Map

```
[Telegram Trigger]
       ↓
[Detect Intent — Claude]   (claude-haiku-4-5-20251001, classify message)
       ↓
[Parse Claude Response]    (Code node: JSON.parse response text)
       ↓
[Route Intent — Switch]
   ├─ output 0: ADD_EXPENSE  → [GitHub: Quick Add] → [Reply: Added]
   ├─ output 1: QUERY_BUDGET → [GitHub: Query Budget] → (GH Actions replies async)
   └─ output 2: UNKNOWN      → [Reply: Unknown]
```

---

## Node 1 — Telegram Trigger

| Field | Value |
|---|---|
| Node type | `n8n-nodes-base.telegramTrigger` |
| Updates | `message` |
| Credential | `Telegram Bot` |

**Webhook secret validation:** In the Telegram Bot node's credential settings, set a secret token. Validate in n8n via Header Auth on the trigger's webhook URL (n8n Pro/Enterprise) or handle it in a Code node:

```js
// Code node after trigger — validate secret
const secret = $env.TELEGRAM_SECRET;
const incoming = $input.first().json.headers['x-telegram-bot-api-secret-token'];
if (incoming !== secret) throw new Error('Unauthorized Telegram request');
return $input.all();
```

Key output fields: `$json.message.text`, `$json.message.chat.id`, `$json.message.from.id`.

---

## Node 2 — Detect Intent (Claude)

**HTTP Request** to Claude API. Uses `claude-haiku-4-5-20251001` for low-latency classification.

| Field | Value |
|---|---|
| Method | `POST` |
| URL | `https://api.anthropic.com/v1/messages` |
| Header: `x-api-key` | `{{ $credentials.claudeApiKey }}` |
| Header: `anthropic-version` | `2023-06-01` |
| Header: `content-type` | `application/json` |

**Body:**
```json
{
  "model": "claude-haiku-4-5-20251001",
  "max_tokens": 150,
  "messages": [{
    "role": "user",
    "content": "User message: {{ $json.message.text }}\n\nClassify as one of:\n- ADD_EXPENSE: user wants to log a spend (extract: merchant, amount, currency, payment_method, notes)\n- QUERY_BUDGET: user asks about spending/budget\n- UNKNOWN\n\nReply with JSON only: {\"intent\": \"ADD_EXPENSE\", \"merchant\": \"\", \"amount\": 0, \"currency\": \"INR\", \"payment_method\": \"upi\", \"notes\": \"\"}\nor {\"intent\": \"QUERY_BUDGET\", \"month\": \"\"}\nor {\"intent\": \"UNKNOWN\"}"
  }]
}
```

**Intent patterns Claude resolves:**
- `"500 zomato dinner"` → `ADD_EXPENSE`, merchant=zomato, amount=500, notes=dinner
- `"petty 50 tea"` → `ADD_EXPENSE`, notes=petty cash tea (budget_type set downstream)
- `"how much left this month?"` → `QUERY_BUDGET`
- `"what's my debt balance?"` → `QUERY_BUDGET`

---

## Node 3 — Parse Claude Response (Code)

```js
const text = $input.first().json.content[0].text.trim();
const parsed = JSON.parse(text);

// Petty cash detection
const originalMsg = $('Telegram Trigger').first().json.message.text.toLowerCase();
if (originalMsg.includes('petty')) {
  parsed.budget_type = 'petty';
}

return [{ json: parsed }];
```

---

## Node 4 — Route Intent (Switch)

| Field | Value |
|---|---|
| Value to check | `={{ $json.intent }}` |
| Rule 0 | equals `ADD_EXPENSE` → output 0 |
| Rule 1 | equals `QUERY_BUDGET` → output 1 |
| Fallback output | 2 (UNKNOWN) |

---

## Node 5 — GitHub: Quick Add (HTTP Request)

Dispatches `quick-add` event. GitHub Actions runs `finance.py add` with the extracted fields.

```json
{
  "event_type": "quick-add",
  "client_payload": {
    "merchant": "={{ $json.merchant }}",
    "amount": "={{ $json.amount }}",
    "currency": "={{ $json.currency || 'INR' }}",
    "payment_method": "={{ $json.payment_method || 'upi' }}",
    "notes": "={{ $json.notes || '' }}",
    "budget_type": "={{ $json.budget_type || '' }}",
    "date": "={{ new Date().toISOString().split('T')[0] }}"
  }
}
```

Same GH API URL and auth as WF1.

---

## Node 6 — GitHub: Query Budget (HTTP Request)

```json
{
  "event_type": "query-budget",
  "client_payload": {
    "month": "={{ $json.month || new Date().toISOString().slice(0,7) }}",
    "chat_id": "={{ $('Telegram Trigger').first().json.message.chat.id }}"
  }
}
```

GitHub Actions handles the Sheets query and sends the Telegram reply directly (async). WF2 does not wait.

---

## Node 7 — Reply: Added (Telegram)

```
✅ Got it! Adding ₹{{ $('Parse Claude Response').first().json.amount }} at {{ $('Parse Claude Response').first().json.merchant }}. I'll categorize it — check your sheet in ~30 seconds.
```

Chat ID: `={{ $('Telegram Trigger').first().json.message.chat.id }}`

---

## Node 8 — Reply: Unknown (Telegram)

```
🤔 Not sure what you mean. Try:
• "Spent 200 at Zomato"
• "How much did I spend this month?"
```

---

## Claude AI Agent Node (alternative to HTTP Request)

If using n8n's native **AI Agent** node instead of raw HTTP:

| Field | Value |
|---|---|
| Node type | `@n8n/n8n-nodes-langchain.agent` |
| Model | `claude-3-5-haiku` via Anthropic credential |
| System prompt | `"You are a personal finance assistant for an Indian user tracking expenses. You have access to their Google Sheets data. Answer questions about spending, budget, debts, and goals. Be concise. Use ₹ for amounts."` |
| Memory | Simple Memory node — window size: 10 messages |
| Tools | Google Sheets Read nodes: Transactions, Budget, Debts, Goals tabs |

---

## Verification

| Test | Expected Result |
|---|---|
| Send `"500 zomato"` | Reply: `✅ Got it! Adding ₹500 at zomato...` + GH Actions `quick-add` run visible |
| Wait 30s, check Transactions sheet | New row with date=today, merchant=zomato, amount=500, currency=INR |
| Send `"50 petty tea"` | Row added with budget_type=petty |
| Send `"how much left this month?"` | Claude replies with budget breakdown from Sheets |
| Send `"asdfgh"` | Reply: `🤔 Not sure what you mean...` |
| Check n8n execution log | All nodes green, no errors |
