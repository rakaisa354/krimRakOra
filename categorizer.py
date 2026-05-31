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

    # deduplicate: call API once per unique merchant, not once per row
    api_cache: dict[str, dict] = {}

    for row in rows:
        merchant_upper = row["merchant"].upper()

        # Layer 1: prefix match in Vendor_Map
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
            continue

        # Layer 2: Claude API inference (cached per unique merchant)
        if merchant_upper not in api_cache:
            message = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=100,
                messages=[{
                    "role": "user",
                    "content": (
                        f"Merchant: {row['merchant']}\n"
                        f"Amount: {row['amount']} {row['currency']}\n\n"
                        f"Pick the best match from these categories:\n{cat_list}\n\n"
                        "Reply with ONLY: category|subcategory|budget_type|confidence (0-100)"
                    )
                }]
            )
            parts = message.content[0].text.strip().split("|")
            if len(parts) == 4:
                api_cache[merchant_upper] = {
                    "category": parts[0].strip(),
                    "subcategory": parts[1].strip(),
                    "budget_type": parts[2].strip(),
                    "_confidence": int(parts[3].strip()) if parts[3].strip().isdigit() else 0,
                }
            else:
                api_cache[merchant_upper] = {"category": "", "subcategory": "", "budget_type": "", "_confidence": 0}

        cached = api_cache[merchant_upper]
        row["category"] = cached["category"]
        row["subcategory"] = cached["subcategory"]
        row["budget_type"] = cached["budget_type"]
        row["_confidence"] = cached["_confidence"]

    return rows
