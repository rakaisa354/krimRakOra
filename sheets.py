import gspread
from google.oauth2.service_account import Credentials
from config import GOOGLE_SHEETS_ID
from scripts.setup_sheets import HEADERS

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.readonly",
]

def get_sheet(tab_name: str):
    creds = Credentials.from_service_account_file("credentials.json", scopes=SCOPES)
    client = gspread.authorize(creds)
    spreadsheet = client.open_by_key(GOOGLE_SHEETS_ID)
    return spreadsheet.worksheet(tab_name)

def append_rows(tab_name: str, rows: list[list]) -> None:
    sheet = get_sheet(tab_name)
    sheet.append_rows(rows, value_input_option="USER_ENTERED")

def read_all(tab_name: str) -> list[dict]:
    sheet = get_sheet(tab_name)
    # expected_headers bypasses gspread's header-uniqueness check, which
    # otherwise trips whenever the sheet's used range is wider than the real
    # header row (stray data pasted into a far column pads row 1 with
    # duplicate blank headers) — see CLAUDE.md Session 2026-08-10.
    return sheet.get_all_records(expected_headers=HEADERS.get(tab_name))

def update_row(tab_name: str, row_number: int, values: list) -> None:
    """Overwrite one data row. row_number is 1-indexed against read_all()'s
    output (i.e. row_number=1 is the first data row, sheet row 2)."""
    sheet = get_sheet(tab_name)
    last_col = chr(ord("A") + len(values) - 1)
    sheet.update(f"A{row_number + 1}:{last_col}{row_number + 1}", [values], value_input_option="USER_ENTERED")
