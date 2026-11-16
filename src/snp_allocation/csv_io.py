import csv
from collections.abc import Iterator, Sequence
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


_SUPPLY_COLUMNS = ('case_id', 'period', 'item', 'source_location', 'available_qty')
_REQUEST_COLUMNS = (
    'case_id',
    'request_id',
    'dest_location',
    'priority',
    'demand_qty',
    'min_lot',
    'rounding_value',
)


def _read_rows(
    path: Path, columns: Sequence[str]
) -> Iterator[tuple[int, dict[str, str]]]:
    with path.open(newline='', encoding='utf-8-sig') as file:
        reader = csv.reader(file, strict=True)
        try:
            header = next(reader, [])
            missing = sorted(set(columns) - set(header))
            if missing:
                raise CsvFormatError(
                    f'{path.name}:1: missing columns: {", ".join(missing)}'
                )
            if len(set(header)) != len(header):
                raise CsvFormatError(f'{path.name}:1: duplicate column names')
            for values in reader:
                if not values:
                    continue
                line = reader.line_num
                if len(values) != len(header):
                    raise CsvFormatError(
                        f'{path.name}:{line}: expected {len(header)} fields, '
                        f'got {len(values)}'
                    )
                row = dict(zip(header, values, strict=True))
                for column in columns:
                    if not row[column].strip():
                        raise CsvFormatError(
                            f'{path.name}:{line}: {column} must not be empty'
                        )
                yield line, row
        except csv.Error as exc:
            raise CsvFormatError(
                f'{path.name}:{reader.line_num}: invalid CSV: {exc}'
            ) from exc


def _to_int(path: Path, line: int, row: dict[str, str], column: str) -> int:
    try:
        return int(row[column])
    except ValueError as exc:
        raise CsvFormatError(
            f'{path.name}:{line}: {column} must be an integer, got {row[column]!r}'
        ) from exc


def load_cases(supply_path: Path, requests_path: Path) -> tuple[list[Case], list[str]]:
    """Load cases and warn about requests referencing an unknown case.

    Malformed headers, rows and numeric values raise CsvFormatError.
    """
    cases: dict[str, Case] = {}
    for line, row in _read_rows(supply_path, _SUPPLY_COLUMNS):
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
    for line, row in _read_rows(requests_path, _REQUEST_COLUMNS):
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
