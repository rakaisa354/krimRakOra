from parsers.icici import parse as parse_icici
from parsers.sbi import parse as parse_sbi
from parsers.scapia import parse as parse_scapia

def detect_card_type(md_content: str) -> str:
    if "Amazon Pay" in md_content or "ICICI Bank" in md_content:
        return "icici"
    if "SBI Card" in md_content:
        return "sbi"
    if "Scapia" in md_content or "Federal" in md_content:
        return "scapia"
    raise ValueError("Unknown card type. Check the MD file header.")

def parse_statement(md_content: str) -> list[dict]:
    card_type = detect_card_type(md_content)
    parsers = {"icici": parse_icici, "sbi": parse_sbi, "scapia": parse_scapia}
    return parsers[card_type](md_content)
