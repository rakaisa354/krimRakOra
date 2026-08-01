from parsers.icici import parse as parse_icici
from parsers.sbi import parse as parse_sbi
from parsers.scapia import parse as parse_scapia
from parsers.rbl import parse as parse_rbl
from parsers.kotak import parse as parse_kotak

def detect_card_type(md_content: str) -> str:
    if "Amazon Pay" in md_content or "ICICI Bank" in md_content:
        return "icici"
    if "SBI Card" in md_content:
        return "sbi"
    if "Scapia" in md_content or "Federal" in md_content:
        return "scapia"
    if "RBL Bank" in md_content:
        return "rbl"
    if "Kotak Mahindra Bank" in md_content:
        return "kotak"
    raise ValueError("Unknown card type. Check the MD file header.")

PARSERS = {"icici": parse_icici, "sbi": parse_sbi, "scapia": parse_scapia,
           "rbl": parse_rbl, "kotak": parse_kotak}

def parse_statement(md_content: str) -> list[dict]:
    card_type = detect_card_type(md_content)
    return PARSERS[card_type](md_content)
