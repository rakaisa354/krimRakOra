from report import _prev_month, _mom_line, _budget_actuals, _overrun_lines


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


def test_budget_actuals_uses_budget_sheet_rows_when_present():
    budget_rows = [{'month': '2026-08', 'budget_type': 'want', 'allocated_inr': 10000}]
    transactions = [{'budget_type': 'want', 'amount_inr': 12000}]
    rows = _budget_actuals('2026-08', budget_rows, transactions, income_total=0)
    assert rows == [{'bt': 'want', 'label': 'Wants', 'alloc': 10000.0, 'actual': 12000.0}]


def test_budget_actuals_falls_back_to_40_30_20_10_split():
    transactions = [{'budget_type': 'need', 'amount_inr': 5000}]
    rows = _budget_actuals('2026-08', [], transactions, income_total=100000)
    need_row = next(r for r in rows if r['bt'] == 'need')
    assert need_row['alloc'] == 40000.0
    assert need_row['actual'] == 5000.0


def test_overrun_lines_flags_two_consecutive_over_budget_months():
    curr = [{'bt': 'want', 'label': 'Wants', 'alloc': 10000, 'actual': 15000}]
    prev = [{'bt': 'want', 'label': 'Wants', 'alloc': 10000, 'actual': 11000}]
    lines = _overrun_lines(curr, prev, '2026-08', '2026-07')
    assert len(lines) == 1
    assert 'Wants' in lines[0]
    assert '150%' in lines[0]
    assert '110%' in lines[0]


def test_overrun_lines_silent_when_only_one_month_over():
    curr = [{'bt': 'want', 'label': 'Wants', 'alloc': 10000, 'actual': 15000}]
    prev = [{'bt': 'want', 'label': 'Wants', 'alloc': 10000, 'actual': 8000}]
    assert _overrun_lines(curr, prev, '2026-08', '2026-07') == []


def test_overrun_lines_silent_when_no_prior_month_data():
    curr = [{'bt': 'want', 'label': 'Wants', 'alloc': 10000, 'actual': 15000}]
    assert _overrun_lines(curr, [], '2026-08', '2026-07') == []
