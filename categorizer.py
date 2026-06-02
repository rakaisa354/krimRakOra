import time
import anthropic
from config import CLAUDE_API_KEY
from sheets import read_all


def categorize_transactions(rows: list[dict]) -> list[dict]:
    client = anthropic.Anthropic(api_key=CLAUDE_API_KEY)
    categories = read_all("Categories")
    vendor_map = read_all("Vendor_Map")
    vendor_lookup = {v["vendor_pattern"].upper(): v for v in vendor_map}

    cat_list = "\n".join(
        f"{c['category']} > {c['subcategory']} ({c['budget_type']})"
        for c in categories
    )

    # Layer 1: Vendor_Map prefix match
    needs_api: list[dict] = []
    for row in rows:
        merchant_upper = row["merchant"].upper()
        matched = next(
            (v for k, v in vendor_lookup.items() if merchant_upper.startswith(k)),
            None
        )
        if matched:
            row["category"] = matched["category"]
            row["subcategory"] = matched["subcategory"]
            row["budget_type"] = next(
                (c["budget_type"] for c in categories
                 if c["category"] == matched["category"]
                 and c["subcategory"] == matched["subcategory"]),
                ""
            )
            row.setdefault("_confidence", 100)
        else:
            needs_api.append(row)

    if not needs_api:
        return rows

    # Layer 2: Batch all uncategorized merchants into ONE Claude call
    # Deduplicate merchants to minimise tokens
    unique_merchants: dict[str, list[dict]] = {}
    for row in needs_api:
        key = row["merchant"].upper()
        unique_merchants.setdefault(key, []).append(row)

    merchant_lines = "\n".join(
        f"{i+1}. {merchant} ({rows_list[0]['amount']} {rows_list[0]['currency']})"
        for i, (merchant, rows_list) in enumerate(unique_merchants.items())
    )

    prompt = (
        f"Categorise each merchant below using ONLY the categories listed.\n\n"
        f"Categories:\n{cat_list}\n\n"
        f"Merchants:\n{merchant_lines}\n\n"
        "Reply with one line per merchant, format exactly:\n"
        "N|category|subcategory|budget_type|confidence\n"
        "where N is the merchant number and confidence is 0-100.\n"
        "No extra text."
    )

    # Retry loop with exponential backoff for rate limits
    for attempt in range(4):
        try:
            message = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=50 * len(unique_merchants),
                messages=[{"role": "user", "content": prompt}]
            )
            break
        except anthropic.RateLimitError:
            wait = 60 * (attempt + 1)
            print(f"  Rate limit hit — waiting {wait}s before retry {attempt + 1}/4...")
            time.sleep(wait)
    else:
        # All retries exhausted — leave categories blank
        print("  ⚠ Claude API rate limit — categories left blank, review manually")
        for row in needs_api:
            row.setdefault("category", "")
            row.setdefault("subcategory", "")
            row.setdefault("budget_type", "")
            row["_confidence"] = 0
        return rows

    # Parse batch response
    result_map: dict[int, dict] = {}
    for line in message.content[0].text.strip().splitlines():
        parts = [p.strip() for p in line.split("|")]
        if len(parts) == 5 and parts[0].isdigit():
            idx = int(parts[0]) - 1
            result_map[idx] = {
                "category": parts[1],
                "subcategory": parts[2],
                "budget_type": parts[3],
                "_confidence": int(parts[4]) if parts[4].isdigit() else 0,
            }

    # Apply results back to all rows
    for i, (merchant_upper, row_list) in enumerate(unique_merchants.items()):
        cat_data = result_map.get(i, {"category": "", "subcategory": "", "budget_type": "", "_confidence": 0})
        for row in row_list:
            row["category"] = cat_data["category"]
            row["subcategory"] = cat_data["subcategory"]
            row["budget_type"] = cat_data["budget_type"]
            row["_confidence"] = cat_data["_confidence"]

    return rows
