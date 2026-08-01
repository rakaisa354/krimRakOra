import pytest
from unittest.mock import patch, MagicMock
import sheets as sheets_module
from sheets import get_sheet, append_rows, read_all


def test_get_sheet_returns_worksheet():
    with patch("sheets.Credentials.from_service_account_file"), \
         patch("sheets.gspread.authorize") as mock_auth:
        mock_client = MagicMock()
        mock_auth.return_value = mock_client
        mock_client.open_by_key.return_value.worksheet.return_value = MagicMock()
        result = get_sheet("Transactions")
        assert result is not None


def test_append_rows_calls_api():
    """
    Direct lambda replacement — avoids all mock framework indirection.
    Captures args written to the fake worksheet.
    """
    import sheets
    captured = []

    class _FakeSheet:
        def append_rows(self, rows, value_input_option=None):
            captured.append({"rows": rows, "option": value_input_option})

    _orig = sheets.get_sheet
    sheets.get_sheet = lambda _tab: _FakeSheet()
    try:
        sheets.append_rows("Transactions", [["2026-05-31", "ICICI", "Zomato", 500]])
    finally:
        sheets.get_sheet = _orig

    assert len(captured) == 1, f"Expected 1 call, got {len(captured)}"
    assert captured[0]["rows"] == [["2026-05-31", "ICICI", "Zomato", 500]]
    assert captured[0]["option"] == "USER_ENTERED"
