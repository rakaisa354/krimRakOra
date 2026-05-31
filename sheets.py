import gspread
from google.oauth2.service_account import Credentials
from config import GOOGLE_SHEETS_ID

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
    return sheet.get_all_records()
