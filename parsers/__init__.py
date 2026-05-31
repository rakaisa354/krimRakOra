from parsers.icici import parse as parse_icici

def detect_card_type(md_content: str) -> str:
    if "Amazon Pay" in md_content or "ICICI Bank" in md_content:
        return "icici"
    raise ValueError("Unknown card type. Check the MD file header.")

def parse_statement(md_content: str) -> list[dict]:
    card_type = detect_card_type(md_content)
    parsers = {"icici": parse_icici}
    return parsers[card_type](md_content)
