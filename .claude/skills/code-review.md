# Skill: code-review

Run this skill after completing any script to verify quality, correctness, and consistency with project conventions.

## Checklist

### 1. Schema compliance
Every parser output row must have ALL 12 fields exactly:
```
date | card_account | merchant | amount | currency | exchange_rate | amount_inr | category | subcategory | budget_type | payment_method | notes
```
- `amount` = original (may be non-INR)
- `amount_inr` = always `convert_to_inr(amount, currency, date)` result
- `exchange_rate` = 1.0 if INR, else from `FX_Rates` sheet
- `category` / `subcategory` / `budget_type` = populated by categorizer (not parser)
- `payment_method` = card name (e.g. "ICICI Amazon Pay CC")
- `notes` = EMI details, reward points, or ""

### 2. Dedup safety
`finance.py parse` must check `(date, merchant, amount_inr)` against existing Transactions before writing. Verify the dedup block exists.

### 3. Error handling
- Every Sheets API call must be wrapped: network errors should print a warning and not silently corrupt data.
- Parser must raise a clear `ValueError` for malformed MD files, not crash with `IndexError`.

### 4. Token efficiency (Claude API)
- `categorizer.py`: single batch call per `parse` run — never one call per transaction.
- `max_tokens` = `50 * len(unique_merchants)` — adjust if responses truncate.
- Model = `claude-haiku-4-5-20251001` — do not upgrade to Sonnet/Opus for categorization.

### 5. Dry-run parity
`--dry-run` flag must show identical rows to what would be written. Verify the dry-run path uses `new_rows`, not `rows`.

### 6. FX handling
Foreign transactions: `exchange_rate` must be fetched from `FX_Rates` sheet via `fx.get_rate(currency, date)`. Never hardcode rates.

### 7. Tests
Run existing pytest suite:
```bash
cd /path/to/krimRakOra && python -m pytest tests/ -v
```
All tests must pass. New code should have at least one test in `tests/`.

## Output
After review, summarise findings as:
```
✓ Schema: PASS
✓ Dedup: PASS
⚠ Error handling: [finding]
✓ Token efficiency: PASS
✓ Dry-run: PASS
✓ FX: PASS
✓ Tests: X passed
```
Log to `docs/superpowers/plans/review-log.txt`.
