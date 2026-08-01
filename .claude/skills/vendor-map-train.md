# vendor-map-train — Vendor_Map Self-Training Loop

Maintains a lookup table so recurring merchants never hit the Claude API twice.

---

## Schema

Sheet tab: `Vendor_Map`

| Column | Type | Description |
|---|---|---|
| `vendor_pattern` | STRING | Uppercased prefix, max 30 chars. The match key. |
| `normalized_name` | STRING | Human-readable merchant name. |
| `category` | STRING | Must match a value in `Categories` sheet. |
| `subcategory` | STRING | Must match a valid subcategory for that category. |
| `confidence` | STRING | `auto` or `user` (see below). |
| `last_seen` | DATE | ISO date of most recent match. Updated on every hit. |

---

## Confidence Values

| Value | Meaning | Set by |
|---|---|---|
| `auto` | Claude inferred this mapping; not yet human-verified | `categorizer.py` after Claude call with score ≥ 80 |
| `user` | Explicitly confirmed correct by user | Telegram inline keyboard confirm (WF2) |

**Only `user` entries are treated as ground truth.** `auto` entries are used for lookup but can be overridden by re-categorization.

---

## How `categorizer.py` Uses Vendor_Map

**Layer 1 — Prefix match (no API call):**
```python
pattern = merchant.upper()[:30]
# Searches vendor_pattern column for exact match
# If found with any confidence: use mapped category/subcategory
# Skips Claude entirely → zero API cost
```

**Layer 2 — Claude batch (fallback):**
- Called only when no Vendor_Map hit exists.
- Sends `merchant + amount` only — never full statement text.
- If Claude confidence ≥ 80: write result to Vendor_Map with `confidence=auto`.
- If Claude confidence < 80: flag for Telegram inline keyboard review (WF1/WF2).

---

## How New Entries Are Added

### Path A: Automatic (via categorizer.py)
After Claude categorizes a new merchant and confidence ≥ 80, `upsert_vendor_map()` is called:

```python
def upsert_vendor_map(merchant: str, category: str, subcategory: str, confidence: str):
    from sheets import get_sheet, read_all
    from datetime import date
    sheet = get_sheet('Vendor_Map')
    existing = read_all('Vendor_Map')
    pattern = merchant.upper()[:30]  # prefix, max 30 chars
    match = next((i for i, v in enumerate(existing) if v['vendor_pattern'] == pattern), None)
    today = date.today().isoformat()
    if match is not None:
        row_num = match + 2  # 1-indexed + header row
        sheet.update(f'A{row_num}:F{row_num}', [[pattern, merchant, category, subcategory, confidence, today]])
    else:
        sheet.append_row([pattern, merchant, category, subcategory, confidence, today])
```

Pass `confidence='auto'` from categorizer.py. Pass `confidence='user'` from Telegram confirm flow.

### Path B: Telegram Confirm (WF2 — confidence upgrade)
When user taps an inline keyboard button to confirm a category:
1. WF2 webhook receives `{merchant, category, subcategory, confirmed: true}`.
2. WF2 calls `upsert_vendor_map(merchant, category, subcategory, confidence='user')`.
3. Entry is updated in-place: same pattern, `confidence` changes from `auto` → `user`.

### Path C: Manual entry
Open `Vendor_Map` sheet directly. Add a row:
```
VENDOR_PATTERN | Merchant Name | category | subcategory | user | 2026-06-07
```
Use `user` confidence for all manually added entries.

---

## When to Manually Curate

- A merchant is **consistently miscategorized** (e.g., "AMAZON" going to Shopping instead of Groceries for Amazon Fresh).
- A new merchant is very obscure and Claude keeps guessing wrong.
- You want to **split a vendor** by subcategory that changes (not supported by prefix match — use notes field instead).

**Fix steps:**
1. Open `Vendor_Map` sheet.
2. Find the row by `vendor_pattern` (sort/filter column A).
3. Update `category`, `subcategory`, and change `confidence` to `user`.
4. Save.

---

## Bulk Review Workflow

1. Open `Vendor_Map` sheet.
2. Filter column E (`confidence`) = `auto`.
3. Scan the `category` column for anything that looks wrong.
4. Fix the category/subcategory for wrong rows.
5. Change `confidence` to `user` for each corrected row.
6. Do this monthly — takes ~5 minutes once the map is populated.

> **Target state:** Top 50 merchants = `user` confidence. Everything else = `auto`. Claude API calls drop to near-zero for recurring merchants.

---

## Verification

After adding or correcting a Vendor_Map entry, confirm the match fires without a Claude call:

```bash
python finance.py parse --file statements/ICICI_Bank.md --dry-run
```

**Expected output for a matched merchant:**
```
[Vendor_Map] ZOMATO → Food & Dining / Food Delivery  (no API call)
```

**If you still see `[Claude]` next to a merchant you just added:** check that `vendor_pattern` in the sheet exactly equals `merchant.upper()[:30]` for that merchant string.
