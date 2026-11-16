from pathlib import Path

from snp_allocation.allocation import Request
from snp_allocation.csv_io import load_cases


def test_load_cases_preserves_metadata_and_groups_interleaved_requests(
    tmp_path: Path,
) -> None:
    supply = tmp_path / 'supply.csv'
    requests = tmp_path / 'requests.csv'
    supply.write_text(
        'item,available_qty,source_location,period,case_id,comment\n'
        'Widget,7,Plant_A,2026-04,C1,ignored\n'
        'Gadget,3,Plant_B,2026-05,C2,ignored\n',
        encoding='utf-8',
    )
    requests.write_text(
        '\ufeffrounding_value,case_id,demand_qty,dest_location,min_lot,request_id,priority,comment\n'
        '1,C2,3,DC_B,0,R1,1,ignored\n'
        '2,C1,6,DC_A,3,R1,2,ignored\n'
        '1,C1,4,DC_C,0,R2,1,ignored\n',
        encoding='utf-8',
    )

    cases, warnings = load_cases(supply, requests)

    assert warnings == []
    assert [
        (case.case_id, case.period, case.item, case.source_location, case.available_qty)
        for case in cases
    ] == [
        ('C1', '2026-04', 'Widget', 'Plant_A', 7),
        ('C2', '2026-05', 'Gadget', 'Plant_B', 3),
    ]
    assert cases[0].requests == [
        Request('R1', 'DC_A', 2, 6, 3, 2),
        Request('R2', 'DC_C', 1, 4, 0, 1),
    ]
    assert cases[1].requests == [Request('R1', 'DC_B', 1, 3, 0, 1)]


def test_load_cases_preserves_supply_when_requests_are_empty(tmp_path: Path) -> None:
    supply = tmp_path / 'supply.csv'
    requests = tmp_path / 'requests.csv'
    supply.write_text(
        'case_id,period,item,source_location,available_qty\n'
        'C1,2026-04,Widget,Plant_A,7\n',
        encoding='utf-8',
    )
    requests.write_text(
        'case_id,request_id,dest_location,priority,demand_qty,min_lot,rounding_value\n',
        encoding='utf-8',
    )

    cases, warnings = load_cases(supply, requests)

    assert warnings == []
    assert len(cases) == 1
    assert cases[0].case_id == 'C1'
    assert cases[0].available_qty == 7
    assert cases[0].requests == []
