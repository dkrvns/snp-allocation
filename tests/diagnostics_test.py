import pytest

from snp_allocation.allocation import Request
from snp_allocation.diagnostics import request_issues


@pytest.mark.parametrize(
    ('priority', 'demand', 'min_lot', 'rounding', 'expected'),
    [
        pytest.param(
            0, 10, 0, 1, ['priority 0 < 1, request excluded'], id='zero-priority'
        ),
        pytest.param(
            -1, 10, 0, 1, ['priority -1 < 1, request excluded'], id='negative-priority'
        ),
        pytest.param(
            1, -1, 0, 1, ['negative demand_qty, request excluded'], id='negative-demand'
        ),
        pytest.param(
            1, 10, -1, 1, ['negative min_lot, request excluded'], id='negative-min-lot'
        ),
        pytest.param(
            1,
            10,
            0,
            -1,
            ['negative rounding_value, request excluded'],
            id='negative-rounding',
        ),
        pytest.param(1, 0, 0, 1, ['zero demand'], id='zero-demand'),
        pytest.param(
            1,
            10,
            0,
            0,
            ['rounding_value 0 treated as 1 (no rounding)'],
            id='zero-rounding',
        ),
        pytest.param(
            1,
            0,
            0,
            0,
            ['zero demand', 'rounding_value 0 treated as 1 (no rounding)'],
            id='all-applicable-warnings',
        ),
        pytest.param(
            1,
            10,
            3,
            2,
            ['min_lot not a multiple of rounding, effective 4'],
            id='effective-min-lot',
        ),
        pytest.param(
            1, 2, 4, 2, ['smallest shipment 4 exceeds demand'], id='small-demand'
        ),
        pytest.param(1, 4, 4, 2, [], id='demand-at-minimum'),
        pytest.param(1, 10, 0, 1, [], id='valid-request'),
    ],
)
def test_request_issues_reports_all_applicable_constraints(
    priority: int, demand: int, min_lot: int, rounding: int, expected: list[str]
) -> None:
    request = Request('R1', 'DC', priority, demand, min_lot, rounding)

    assert request_issues(request) == expected
