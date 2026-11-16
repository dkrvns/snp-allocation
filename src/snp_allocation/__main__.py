import argparse
from collections.abc import Sequence
from pathlib import Path

from snp_allocation.allocation import AllocationInputError, allocate
from snp_allocation.csv_io import Case, CsvFormatError, load_cases
from snp_allocation.diagnostics import request_issues

HEADER = (
    f'  {"request":<8} {"dest":<6} {"prio":>4} {"demand":>6} {"min_lot":>7} '
    f'{"round":>5} {"shipped":>7} {"fill":>6}'
)


def _format_case(case: Case) -> str:
    shipped = allocate(case.available_qty, case.requests)
    lines = [
        f'{case.case_id}  {case.period} {case.item} from {case.source_location}, '
        f'available {case.available_qty}',
        HEADER,
    ]
    notes: list[str] = []
    for request in sorted(case.requests, key=lambda r: (r.priority, r.request_id)):
        qty = shipped[request.request_id]
        fill = f'{qty / request.demand_qty:.0%}' if request.demand_qty > 0 else '-'
        lines.append(
            f'  {request.request_id:<8} {request.dest_location:<6} '
            f'{request.priority:>4} {request.demand_qty:>6} '
            f'{request.min_lot:>7} {request.rounding_value:>5} '
            f'{qty:>7} {fill:>6}'
        )
        notes.extend(
            f'  ! {request.request_id}: {issue}' for issue in request_issues(request)
        )

    total = sum(shipped.values())
    lines.append(f'  shipped {total}, unallocated {case.available_qty - total}')
    return '\n'.join(lines + notes)


def main(argv: Sequence[str] | None = None) -> None:
    data_dir = Path(__file__).resolve().parents[2] / 'data'
    parser = argparse.ArgumentParser(description='Allocate scarce supply per case.')
    parser.add_argument('--supply', type=Path, default=data_dir / 'supply.csv')
    parser.add_argument('--requests', type=Path, default=data_dir / 'requests.csv')
    args = parser.parse_args(argv)

    try:
        cases, warnings = load_cases(args.supply, args.requests)
        output = '\n\n'.join(_format_case(case) for case in cases)
    except (OSError, UnicodeError, CsvFormatError, AllocationInputError) as exc:
        parser.error(str(exc))
    print(output)
    for warning in warnings:
        print(f'! {warning}')


if __name__ == '__main__':
    main()
