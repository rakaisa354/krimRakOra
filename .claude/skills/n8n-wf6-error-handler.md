# n8n WF6 — Error Handler

**Job:** Receive error events from all other workflows → send Telegram alert → write dead-letter file to Drive for any execution with raw payload data. This is the single pane of glass for all krimRakOra workflow failures.

---

## Credentials Required

| Credential Name (n8n vault) | Type | Used by |
|---|---|---|
| `Telegram Bot` | Telegram API | Alert message |
| `Google Drive OAuth` | OAuth2 | Dead-letter file upload |

---

## Registering WF6 as Error Workflow

In **every other workflow** (WF1–WF5):
1. Open workflow → **Settings** (gear icon, top right)
2. **Error Workflow** → select `WF6 — Error Handler`
3. Save

This routes all unhandled node errors to WF6 automatically.

> **Node-level retry** (separate from WF6): On each critical node (HTTP Requests, Sheets writes), click the node → **Settings** tab → enable `Retry On Fail`, set `Max Tries: 3`, `Wait Between Tries: 1000ms`. Node retries happen first; only if all retries fail does the error propagate to WF6.

---

## Error Payload Structure

When WF6 receives an error, `$json` contains:

```json
{
  "execution": {
    "id": "abc123",
    "url": "https://your-n8n.com/execution/abc123"
  },
  "workflow": {
    "id": "wf-001",
    "name": "WF1 — Drive Statement → GitHub Parse"
  },
  "node": {
    "name": "Trigger GitHub Parse",
    "type": "n8n-nodes-base.httpRequest"
  },
  "error": {
    "message": "Request failed with status code 401",
    "stack": "..."
  },
  "lastNodeExecuted": "Trigger GitHub Parse"
}
```

---

## Node Map

```
[Error Trigger]
      ↓
[Code: Build Alert]
      ↓
[Telegram: Send Alert]
      ↓
[Switch: Has Raw Data?]
   ├─ yes → [Drive: Upload Dead-Letter File]
   └─ no  → (end)
```

---

## Node 1 — Error Trigger

| Field | Value |
|---|---|
| Node type | `n8n-nodes-base.errorTrigger` |
| No configuration needed | Activates automatically when set as error workflow |

---

## Node 2 — Code: Build Alert

```js
const payload = $input.first().json;

const wfName   = payload.workflow?.name || 'Unknown Workflow';
const nodeName = payload.node?.name || payload.lastNodeExecuted || 'Unknown Node';
const errMsg   = payload.error?.message || 'No error message';
const execId   = payload.execution?.id || 'N/A';
const execUrl  = payload.execution?.url || '';
const ts       = new Date().toISOString();

const alertText = `🚨 Workflow error
Workflow: ${wfName}
Node: ${nodeName}
Error: ${errMsg}
Execution: ${execId}
${execUrl ? 'URL: ' + execUrl : ''}
Time: ${ts}`;

// Dead-letter: capture if there's input data worth preserving
const hasData = payload.data || payload.inputData || payload.error?.stack;

return [{
  json: {
    alertText,
    hasData: !!hasData,
    deadLetterContent: JSON.stringify(payload, null, 2),
    deadLetterFilename: `dead-letter/${wfName.replace(/[^a-zA-Z0-9]/g, '_')}_${ts.replace(/[:.]/g, '-')}.json`,
    wfName,
    ts
  }
}];
```

---

## Node 3 — Telegram: Send Alert

| Field | Value |
|---|---|
| Node type | `n8n-nodes-base.telegram` |
| Operation | `sendMessage` |
| Chat ID | Your personal Telegram chat ID (hardcode) |
| Text | `={{ $json.alertText }}` |
| Parse mode | Leave blank (plain text) |

---

## Node 4 — Switch: Has Raw Data?

| Field | Value |
|---|---|
| Value | `={{ $json.hasData }}` |
| Rule 0 | equals `true` → output 0 (upload dead-letter) |
| Fallback | output 1 (end, no file needed) |

---

## Node 5 — Drive: Upload Dead-Letter File

| Field | Value |
|---|---|
| Node type | `n8n-nodes-base.googleDrive` |
| Operation | `upload` |
| File name | `={{ $json.deadLetterFilename }}` |
| File content | `={{ $json.deadLetterContent }}` |
| MIME type | `application/json` |
| Parent folder | Drive folder ID for `dead-letter/` |

The `dead-letter/` folder must exist in Drive before activation.

---

## Node Retry Configuration (per-node, not WF6)

Set on each critical node in WF1–WF5:

| Setting | Value |
|---|---|
| Retry on fail | ✅ enabled |
| Max tries | 3 |
| Wait between tries | 1000ms (1 second) |

Only errors surviving all 3 retries reach WF6.

---

## Verification

### Test 1 — Basic Alert
1. Create a throwaway workflow `WF-Test-Error`.
2. Add an **HTTP Request** node pointing to `https://httpstat.us/500` (always returns 500).
3. In WF-Test-Error Settings → Error Workflow → `WF6 — Error Handler`.
4. Execute WF-Test-Error.
5. **Expected:** Telegram alert arrives within 10 seconds with workflow name, node name, and error message.

### Test 2 — Dead-Letter File
1. Same test workflow, but add a **Set** node before HTTP Request with some data (simulates input payload).
2. Execute → after Telegram alert, check Drive `dead-letter/` folder.
3. **Expected:** JSON file named `WF_Test_Error_<timestamp>.json` exists with full error payload.

### Test 3 — WF1 Error Coverage
1. In WF1, temporarily set an invalid GitHub PAT.
2. Upload a test file to Drive → WF1 triggers → GitHub dispatch fails.
3. **Expected:** Telegram alert with `Workflow: WF1 — Drive Statement → GitHub Parse` and `Node: Trigger GitHub Parse`.
4. Restore correct PAT after verification.
