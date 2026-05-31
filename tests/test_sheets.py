import pytest
from unittest.mock import patch, MagicMock
from sheets import get_sheet, append_rows, read_all

def test_get_sheet_returns_worksheet():
    with patch("sheets.gspread.authorize") as mock_auth:
        mock_client = MagicMock()
        mock_auth.return_value = mock_client
        mock_client.open_by_key.return_value.worksheet.return_value = MagicMock()
        result = get_sheet("Transactions")
        assert result is not None

def test_append_rows_calls_api():
    with patch("sheets.get_sheet") as mock_get:
        mock_ws = MagicMock()
        mock_get.return_value = mock_ws
        append_rows("Transactions", [["2026-05-31", "ICICI", "Zomato", 500]])
        mock_ws.append_rows.assert_called_once()
