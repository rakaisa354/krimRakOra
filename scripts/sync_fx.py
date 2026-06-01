"""Daily FX rate sync — fetches rates for all active currencies and appends to FX_Rates sheet."""

import requests
from datetime import date
from sheets import read_all, get_sheet
from config import FX_API_KEY

CURRENCIES = ["USD", "GBP", "EUR", "SGD", "AED", "THB", "MYR", "JPY"]
BASE = "INR"

def sync():
    today = date.today().isoformat()

    # check if today already synced
    existing = read_all("FX_Rates")
    already_synced = {r["currency_code"] for r in existing if r["date"] == today}

    url = f"https://v6.exchangerate-api.com/v6/{FX_API_KEY}/latest/{BASE}"
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    data = resp.json()

    if data["result"] != "success":
        raise RuntimeError(f"FX API error: {data}")

    rates = data["conversion_rates"]
    sheet = get_sheet("FX_Rates")
    rows = []

    for currency in CURRENCIES:
        if currency in already_synced:
            print(f"  skipped {currency} (already synced today)")
            continue
        if currency not in rates:
            print(f"  ⚠ {currency} not in API response")
            continue
        # API gives rates FROM INR — we want rate TO INR
        # e.g. 1 INR = 0.012 USD → 1 USD = 1/0.012 INR
        rate_from_inr = rates[currency]
        if not rate_from_inr:
            print(f"  ⚠ {currency} rate is zero — skipping")
            continue
        rate_to_inr = round(1 / rate_from_inr, 6)
        rows.append([today, currency, rate_to_inr])
        print(f"  ✓ {currency}: 1 {currency} = {rate_to_inr} INR")

    if rows:
        sheet.append_rows(rows)
        print(f"\n✓ {len(rows)} rates synced for {today}")
    else:
        print(f"✓ All rates already synced for {today}")

if __name__ == "__main__":
    sync()
