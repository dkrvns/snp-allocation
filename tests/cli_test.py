from pathlib import Path

import pytest

from snp_allocation.__main__ import main

DATA_DIR = Path(__file__).resolve().parents[1] / 'data'


def test_main_prints_all_sample_cases_and_diagnostics(
    capsys: pytest.CaptureFixture[str],
) -> None:
    main(
        [
            '--supply',
            str(DATA_DIR / 'supply.csv'),
            '--requests',
            str(DATA_DIR / 'requests.csv'),
        ]
    )

    captured = capsys.readouterr()
    assert captured.err == ''
    assert captured.out.count(' from ') == 7
    assert 'CASE_07' in captured.out
    assert 'shipped 184, unallocated 16' in captured.out
    assert 'R-302: negative demand_qty, request excluded' in captured.out


def test_main_reports_missing_file_without_traceback(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    missing_path = tmp_path / 'missing.csv'

    with pytest.raises(SystemExit) as exc_info:
        main(['--supply', str(missing_path)])

    captured = capsys.readouterr()
    assert exc_info.value.code == 2
    assert captured.out == ''
    assert 'missing.csv' in captured.err
    assert 'Traceback' not in captured.err


@pytest.mark.parametrize(
    ('rows', 'message'),
    [
        pytest.param('C1,2026-01,ITEM,PLANT,invalid\n', 'integer', id='invalid-csv'),
        pytest.param(
            'C1,2026-01,ITEM,PLANT,-1\n', 'non-negative', id='negative-supply'
        ),
        pytest.param(
            'C1,2026-01,ITEM,PLANT,10\nC2,2026-01,ITEM,PLANT,-1\n',
            'non-negative',
            id='invalid-second-case',
        ),
    ],
)
def test_main_rejects_bad_input_without_partial_output(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    rows: str,
    message: str,
) -> None:
    supply_path = tmp_path / 'supply.csv'
    requests_path = tmp_path / 'requests.csv'
    supply_path.write_text(
        'case_id,period,item,source_location,available_qty\n' + rows,
        encoding='utf-8',
    )
    requests_path.write_text(
        'case_id,request_id,dest_location,priority,demand_qty,min_lot,rounding_value\n',
        encoding='utf-8',
    )

    with pytest.raises(SystemExit) as exc_info:
        main(['--supply', str(supply_path), '--requests', str(requests_path)])

    captured = capsys.readouterr()
    assert exc_info.value.code == 2
    assert captured.out == ''
    assert message in captured.err
    assert 'Traceback' not in captured.err
