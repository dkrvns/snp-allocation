from pathlib import Path

import pytest

from snp_allocation.allocation import Request
from snp_allocation.csv_io import CsvFormatError, load_cases

SUPPLY_HEADER = 'case_id,period,item,source_location,available_qty\n'
REQUEST_HEADER = (
    'case_id,request_id,dest_location,priority,demand_qty,min_lot,rounding_value\n'
)
SUPPLY_ROW = 'C1,2026-01,ITEM,PLANT,10\n'
REQUEST_ROW = 'C1,R1,DC,1,10,0,1\n'


def _write_inputs(
    tmp_path: Path,
    *,
    supply: str = SUPPLY_HEADER + SUPPLY_ROW,
    requests: str = REQUEST_HEADER + REQUEST_ROW,
) -> tuple[Path, Path]:
    supply_path = tmp_path / 'supply.csv'
    requests_path = tmp_path / 'requests.csv'
    supply_path.write_text(supply, encoding='utf-8')
    requests_path.write_text(requests, encoding='utf-8')
    return supply_path, requests_path


@pytest.mark.parametrize(
    ('supply', 'message'),
    [
        pytest.param('', 'missing columns', id='empty-file'),
        pytest.param('case_id\nC1\n', 'missing columns', id='missing-columns'),
        pytest.param(
            SUPPLY_HEADER.rstrip() + ',case_id\n',
            'duplicate column names',
            id='duplicate-columns',
        ),
        pytest.param(
            SUPPLY_HEADER + 'C1,2026-01,ITEM,PLANT\n',
            'supply.csv:2: expected 5 fields, got 4',
            id='short-row',
        ),
        pytest.param(
            SUPPLY_HEADER + 'C1,2026-01,ITEM,PLANT,10,extra\n',
            'supply.csv:2: expected 5 fields, got 6',
            id='long-row',
        ),
        pytest.param(
            SUPPLY_HEADER + ' ,2026-01,ITEM,PLANT,10\n',
            'case_id must not be empty',
            id='empty-identity',
        ),
        pytest.param(
            SUPPLY_HEADER + 'C1,2026-01,ITEM,PLANT,1.5\n',
            'available_qty must be an integer',
            id='non-integer-quantity',
        ),
        pytest.param(
            SUPPLY_HEADER + 'C1,2026-01,"ITEM,PLANT,10\n',
            'invalid CSV',
            id='unclosed-quote',
        ),
        pytest.param(
            SUPPLY_HEADER + SUPPLY_ROW * 2,
            'supply.csv:3: duplicate C1',
            id='duplicate-case',
        ),
    ],
)
def test_load_cases_rejects_malformed_supply(
    tmp_path: Path, supply: str, message: str
) -> None:
    paths = _write_inputs(tmp_path, supply=supply)

    with pytest.raises(CsvFormatError, match=message):
        load_cases(*paths)


@pytest.mark.parametrize(
    ('requests', 'message'),
    [
        pytest.param('case_id\n', 'missing columns', id='missing-columns'),
        pytest.param(
            REQUEST_HEADER + 'C1,R1,DC,1,10,0\n',
            'requests.csv:2: expected 7 fields, got 6',
            id='short-row',
        ),
        pytest.param(
            REQUEST_HEADER + 'C1,,DC,1,10,0,1\n',
            'request_id must not be empty',
            id='empty-identity',
        ),
        pytest.param(
            REQUEST_HEADER + 'C1,R1,DC,high,10,0,1\n',
            'requests.csv:2: priority must be an integer',
            id='invalid-priority',
        ),
    ],
)
def test_load_cases_rejects_malformed_requests(
    tmp_path: Path, requests: str, message: str
) -> None:
    paths = _write_inputs(tmp_path, requests=requests)

    with pytest.raises(CsvFormatError, match=message):
        load_cases(*paths)


def test_load_cases_preserves_bom_blank_lines_and_quoted_values(tmp_path: Path) -> None:
    paths = _write_inputs(
        tmp_path,
        supply='\ufeff' + SUPPLY_HEADER + '\nC1,2026-01,"ITEM, A",PLANT,10\n',
    )

    cases, warnings = load_cases(*paths)

    assert warnings == []
    assert len(cases) == 1
    assert cases[0].case_id == 'C1'
    assert cases[0].item == 'ITEM, A'
    assert cases[0].available_qty == 10
    assert cases[0].requests == [Request('R1', 'DC', 1, 10, 0, 1)]


def test_load_cases_reports_physical_line_after_blank_and_multiline_rows(
    tmp_path: Path,
) -> None:
    paths = _write_inputs(
        tmp_path,
        supply=SUPPLY_HEADER + '\nC1,2026-01,"ITEM\nA",PLANT,10\n'
        'C2,2026-01,ITEM,PLANT,invalid\n',
    )

    with pytest.raises(CsvFormatError, match=r'supply\.csv:5: available_qty'):
        load_cases(*paths)


def test_load_cases_skips_unknown_case_with_warning(tmp_path: Path) -> None:
    paths = _write_inputs(
        tmp_path,
        requests=REQUEST_HEADER + REQUEST_ROW + 'UNKNOWN,R2,DC,1,10,0,1\n',
    )

    cases, warnings = load_cases(*paths)

    assert len(cases) == 1
    assert cases[0].requests == [Request('R1', 'DC', 1, 10, 0, 1)]
    assert warnings == ['requests.csv:3: unknown case UNKNOWN, skipped']


def test_load_cases_accepts_header_only_files(tmp_path: Path) -> None:
    paths = _write_inputs(tmp_path, supply=SUPPLY_HEADER, requests=REQUEST_HEADER)

    assert load_cases(*paths) == ([], [])
