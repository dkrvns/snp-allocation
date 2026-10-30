import csv
from dataclasses import dataclass, field
from pathlib import Path

from snp_allocation.allocation import Request


class CsvFormatError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class Case:
    case_id: str
    period: str
    item: str
    source_location: str
    available_qty: int
    requests: list[Request] = field(default_factory=list)


def _read_rows(path: Path) -> list[tuple[int, dict[str, str]]]:
    with path.open(newline='', encoding='utf-8-sig') as file:
        return [(line, row) for line, row in enumerate(csv.DictReader(file), start=2)]


def _to_int(path: Path, line: int, row: dict[str, str], column: str) -> int:
    try:
        return int(row[column])
    except (KeyError, TypeError, ValueError) as e:
        raise CsvFormatError(
            f'{path.name}:{line}: {column} must be an integer, got {row.get(column)!r}'
        ) from e


def load_cases(supply_path: Path, requests_path: Path) -> tuple[list[Case], list[str]]:
    cases: dict[str, Case] = {}
    for line, row in _read_rows(supply_path):
        case_id = row['case_id']
        if case_id in cases:
            raise CsvFormatError(f'{supply_path.name}:{line}: duplicate {case_id}')
        cases[case_id] = Case(
            case_id=case_id,
            period=row['period'],
            item=row['item'],
            source_location=row['source_location'],
            available_qty=_to_int(supply_path, line, row, 'available_qty'),
        )

    warnings = []
    for line, row in _read_rows(requests_path):
        request = Request(
            request_id=row['request_id'],
            dest_location=row['dest_location'],
            priority=_to_int(requests_path, line, row, 'priority'),
            demand_qty=_to_int(requests_path, line, row, 'demand_qty'),
            min_lot=_to_int(requests_path, line, row, 'min_lot'),
            rounding_value=_to_int(requests_path, line, row, 'rounding_value'),
        )
        case = cases.get(row['case_id'])
        if case is None:
            warnings.append(
                f'{requests_path.name}:{line}: unknown case {row["case_id"]}, skipped'
            )
            continue
        case.requests.append(request)
    return list(cases.values()), warnings
