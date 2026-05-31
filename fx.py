from sheets import read_all

def get_rate(currency: str, date: str) -> float:
    if currency == "INR":
        return 1.0
    rows = read_all("FX_Rates")
    matches = [r for r in rows if r["currency_code"] == currency]
    if not matches:
        raise ValueError(f"No FX rate found for {currency}. Add it to FX_Rates sheet.")
    exact = [r for r in matches if r["date"] == date]
    row = exact[0] if exact else sorted(matches, key=lambda r: r["date"])[-1]
    return float(row["rate_to_inr"])

def convert_to_inr(amount: float, currency: str, date: str) -> float:
    if currency == "INR":
        return amount
    rate = get_rate(currency, date)
    return round(amount * rate, 2)
