from snp_allocation.allocation import Lot, Request


def request_issues(request: Request) -> list[str]:
    if request.priority < 1:
        return [f'priority {request.priority} < 1, request excluded']
    for field in ('demand_qty', 'min_lot', 'rounding_value'):
        if getattr(request, field) < 0:
            return [f'negative {field}, request excluded']

    issues = []
    if request.demand_qty == 0:
        issues.append('zero demand')
    if request.rounding_value == 0:
        issues.append('rounding_value 0 treated as 1 (no rounding)')
    lot = Lot.of(request)
    if request.min_lot > 0 and lot.first != request.min_lot:
        issues.append(f'min_lot not a multiple of rounding, effective {lot.first}')
    if 0 < request.demand_qty < lot.first:
        issues.append(f'smallest shipment {lot.first} exceeds demand')
    return issues
