import subprocess
import sys
from pathlib import Path

import pytest

from snp_allocation.__main__ import main


@pytest.fixture
def cli_inputs(tmp_path: Path) -> tuple[Path, Path]:
    supply = tmp_path / 'supply.csv'
    requests = tmp_path / 'requests.csv'
    supply.write_text(
        'case_id,period,item,source_location,available_qty\n'
        'C1,2026-04,Widget,Plant,7\n',
        encoding='utf-8',
    )
    requests.write_text(
        'case_id,request_id,dest_location,priority,demand_qty,min_lot,rounding_value\n'
        'C1,B,DC_B,1,4,0,1\n'
        'C1,A,DC_A,1,6,0,1\n',
        encoding='utf-8',
    )
    return supply, requests


@pytest.mark.parametrize('entrypoint', ['module', 'console-script'])
def test_cli_entrypoint_prints_exact_allocation(
    cli_inputs: tuple[Path, Path], tmp_path: Path, entrypoint: str
) -> None:
    supply, requests = cli_inputs
    command = (
        [sys.executable, '-m', 'snp_allocation']
        if entrypoint == 'module'
        else [str(Path(sys.executable).with_name('snp-allocation'))]
    )

    result = subprocess.run(
        [*command, '--supply', str(supply), '--requests', str(requests)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=5,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert result.stderr == ''
    lines = result.stdout.splitlines()
    assert len(lines) == 5
    assert lines[0] == 'C1  2026-04 Widget from Plant, available 7'
    assert lines[1].split() == [
        'request',
        'dest',
        'prio',
        'demand',
        'min_lot',
        'round',
        'shipped',
        'fill',
    ]
    assert lines[2].split() == ['A', 'DC_A', '1', '6', '0', '1', '4', '67%']
    assert lines[3].split() == ['B', 'DC_B', '1', '4', '0', '1', '3', '75%']
    assert lines[4] == '  shipped 7, unallocated 0'


def test_main_prints_unknown_case_warning(
    cli_inputs: tuple[Path, Path], capsys: pytest.CaptureFixture[str]
) -> None:
    supply, requests = cli_inputs
    with requests.open('a', encoding='utf-8') as file:
        file.write('Missing,Z,DC_Z,1,2,0,1\n')

    main(['--supply', str(supply), '--requests', str(requests)])

    output = capsys.readouterr()
    assert output.err == ''
    assert '  shipped 7, unallocated 0\n' in output.out
    assert output.out.splitlines()[-1] == (
        '! requests.csv:4: unknown case Missing, skipped'
    )


def test_main_rejects_non_utf8_input_without_traceback_or_partial_plan(
    cli_inputs: tuple[Path, Path], capsys: pytest.CaptureFixture[str]
) -> None:
    supply, requests = cli_inputs
    requests.write_bytes(b'\xff')

    with pytest.raises(SystemExit) as error:
        main(['--supply', str(supply), '--requests', str(requests)])

    output = capsys.readouterr()
    assert error.value.code == 2
    assert output.out == ''
    assert 'error:' in output.err
    assert 'decode' in output.err
    assert 'Traceback' not in output.err


def test_main_rejects_duplicate_request_ids_without_partial_plan(
    cli_inputs: tuple[Path, Path], capsys: pytest.CaptureFixture[str]
) -> None:
    supply, requests = cli_inputs
    with requests.open('a', encoding='utf-8') as file:
        file.write('C1,A,DC_C,2,2,0,1\n')

    with pytest.raises(SystemExit) as error:
        main(['--supply', str(supply), '--requests', str(requests)])

    output = capsys.readouterr()
    assert error.value.code == 2
    assert output.out == ''
    assert 'request_id must be unique' in output.err
    assert 'Traceback' not in output.err
