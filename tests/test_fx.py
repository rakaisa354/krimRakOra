import pytest
from unittest.mock import patch, MagicMock
import sys

# Mock sheets.read_all before importing fx, then restore sys.modules so
# later test files (e.g. test_sheets.py) get the real sheets module again.
_real_sheets = sys.modules.get('sheets')
sys.modules['sheets'] = MagicMock()
from fx import convert_to_inr, get_rate
if _real_sheets is not None:
    sys.modules['sheets'] = _real_sheets
else:
    del sys.modules['sheets']

def test_inr_returns_same_amount():
    assert convert_to_inr(1000.0, "INR", "2026-05-31") == 1000.0

def test_usd_conversion_uses_rate():
    with patch("fx.read_all") as mock_read:
        mock_read.return_value = [
            {"date": "2026-05-31", "currency_code": "USD", "rate_to_inr": "83.42"}
        ]
        result = convert_to_inr(100.0, "USD", "2026-05-31")
        assert result == pytest.approx(8342.0, rel=1e-3)

def test_get_rate_raises_for_missing_currency():
    with patch("fx.read_all") as mock_read:
        mock_read.return_value = []
        with pytest.raises(ValueError, match="No FX rate found"):
            get_rate("XYZ", "2026-05-31")

def test_fallback_to_most_recent_rate():
    with patch("fx.read_all") as mock_read:
        mock_read.return_value = [
            {"date": "2026-05-29", "currency_code": "USD", "rate_to_inr": "83.10"},
            {"date": "2026-05-30", "currency_code": "USD", "rate_to_inr": "83.42"},
        ]
        # request date 2026-05-31 has no exact match — should fall back to most recent (05-30)
        rate = get_rate("USD", "2026-05-31")
        assert rate == pytest.approx(83.42, rel=1e-3)
