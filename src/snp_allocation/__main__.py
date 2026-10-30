import argparse
from pathlib import Path

from snp_allocation.allocation import allocate
from snp_allocation.csv_io import Case, load_cases
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
    notes = []
    for r in sorted(case.requests, key=lambda r: (r.priority, r.request_id)):
        qty = shipped[r.request_id]
        fill = f'{qty / r.demand_qty:.0%}' if r.demand_qty > 0 else '-'
        lines.append(
            f'  {r.request_id:<8} {r.dest_location:<6} {r.priority:>4} '
            f'{r.demand_qty:>6} {r.min_lot:>7} {r.rounding_value:>5} '
            f'{qty:>7} {fill:>6}'
        )
        notes.extend(f'  ! {r.request_id}: {issue}' for issue in request_issues(r))

    total = sum(shipped.values())
    lines.append(f'  shipped {total}, unallocated {case.available_qty - total}')
    return '\n'.join(lines + notes)


def main() -> None:
    data_dir = Path(__file__).resolve().parents[2] / 'data'
    parser = argparse.ArgumentParser(description='Allocate scarce supply per case.')
    parser.add_argument('--supply', type=Path, default=data_dir / 'supply.csv')
    parser.add_argument('--requests', type=Path, default=data_dir / 'requests.csv')
    args = parser.parse_args()

    cases, warnings = load_cases(args.supply, args.requests)
    print('\n\n'.join(_format_case(case) for case in cases))
    for warning in warnings:
        print(f'! {warning}')


if __name__ == '__main__':
    main()
