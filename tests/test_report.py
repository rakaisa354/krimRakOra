from report import _prev_month, _mom_line


def test_prev_month_mid_year():
    assert _prev_month('2026-08') == '2026-07'


def test_prev_month_year_rollover():
    assert _prev_month('2026-01') == '2025-12'


def test_mom_line_no_prior_data():
    assert 'no 2026-07 data' in _mom_line('Income', 1000, 0, '2026-07')


def test_mom_line_increase():
    line = _mom_line('Spent', 1500, 1000, '2026-07')
    assert '▲' in line
    assert '+50%' in line


def test_mom_line_decrease():
    line = _mom_line('Spent', 500, 1000, '2026-07')
    assert '▼' in line
    assert '-50%' in line


def test_mom_line_handles_negative_prior():
    # a month that netted negative (credits outweighed spend) shouldn't crash the % calc
    line = _mom_line('Saved', 39047, -9704, '2026-07')
    assert '▲' in line
