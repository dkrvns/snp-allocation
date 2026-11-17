import random
from dataclasses import replace
from fractions import Fraction
from itertools import permutations

import pytest

from snp_allocation.allocation import Request, allocate


@pytest.mark.parametrize(
    'invalid_fields',
    [
        pytest.param({'priority': 0}, id='zero-priority'),
        pytest.param({'priority': -1}, id='negative-priority'),
        pytest.param({'demand_qty': -1}, id='negative-demand'),
        pytest.param({'min_lot': -1}, id='negative-min-lot'),
        pytest.param({'rounding_value': -1}, id='negative-rounding'),
    ],
)
def test_allocate_excludes_invalid_request_without_consuming_supply(
    invalid_fields: dict[str, int],
) -> None:
    invalid = replace(Request('A', 'DC_A', 1, 9, 0, 1), **invalid_fields)
    valid = Request('B', 'DC_B', 2, 5, 0, 1)

    assert allocate(11, [invalid, valid]) == {'A': 0, 'B': 5}


def test_allocate_zero_rounding_allows_an_odd_shipment() -> None:
    request = Request('A', 'DC_A', 1, 9, 0, 0)

    assert allocate(7, [request]) == {'A': 7}


def test_allocate_uses_exact_fill_rate_for_large_integer_demands() -> None:
    initial_lot = 2**60
    requests = [
        Request('A', 'DC_A', 1, 2 * initial_lot, initial_lot, 1),
        Request('B', 'DC_B', 1, 2 * initial_lot + 1, initial_lot, 1),
        Request('C', 'DC_C', 1, 3 * initial_lot, 3 * initial_lot, 1),
    ]

    shipped = allocate(2 * initial_lot + 3, requests)

    # A and B get their initial lots; C cannot fit. The last three units go
    # B, A, B by exact fractions. Float collapses all these rates to 0.5.
    assert shipped == {'A': initial_lot + 1, 'B': initial_lot + 2, 'C': 0}


def test_allocate_accepts_a_single_pass_iterable_without_mutating_requests() -> None:
    requests = [Request('A', 'DC_A', 2, 10), Request('B', 'DC_B', 1, 8, 0, 3)]
    original = requests.copy()

    assert allocate(13, iter(requests)) == {'A': 4, 'B': 9}
    assert requests == original


def test_allocate_breaks_equal_fill_ties_by_lexical_request_id() -> None:
    requests = [Request(name, f'DC_{name}', 1, 3, 0, 1) for name in ('R2', 'R10', 'R1')]

    for ordering in permutations(requests):
        assert allocate(2, ordering) == {'R1': 1, 'R10': 1, 'R2': 0}


def _enumerated_plan(available: int, requests: list[Request]) -> dict[str, int]:
    """Slow oracle: enumerate valid quantities, then follow the published rule."""
    shipped = {request.request_id: 0 for request in requests}
    valid = [
        request
        for request in requests
        if request.priority > 0
        and request.demand_qty > 0
        and request.min_lot >= 0
        and request.rounding_value >= 0
    ]
    quantities = {
        request.request_id: [
            quantity
            for quantity in range(
                1,
                max(request.demand_qty, request.min_lot)
                + max(1, request.rounding_value)
                + 1,
            )
            if quantity >= request.min_lot
            and quantity % max(1, request.rounding_value) == 0
        ]
        for request in valid
    }

    def order(request: Request) -> tuple[Fraction, str]:
        return Fraction(
            shipped[request.request_id], request.demand_qty
        ), request.request_id

    for priority in sorted({request.priority for request in valid}):
        level = [request for request in valid if request.priority == priority]
        active = level.copy()
        while active:
            request = min(active, key=order)
            current = shipped[request.request_id]
            candidates = [
                quantity
                for quantity in quantities[request.request_id]
                if current < quantity <= request.demand_qty
            ]
            if not candidates or candidates[0] - current > available:
                active.remove(request)
                continue
            shipped[request.request_id] = candidates[0]
            available -= candidates[0] - current

        for request in sorted(level, key=order):
            current = shipped[request.request_id]
            target = min(
                quantity
                for quantity in quantities[request.request_id]
                if quantity >= request.demand_qty
            )
            if current < request.demand_qty and target - current <= available:
                shipped[request.request_id] = target
                available -= target - current
    return shipped


def test_allocate_matches_oracle_across_priorities_and_invalid_data() -> None:
    rng = random.Random(41)
    for _ in range(1000):
        requests = [
            Request(
                request_id=f'R{index}',
                dest_location=f'DC_{index}',
                priority=rng.randint(0, 3),
                demand_qty=rng.randint(-1, 25),
                min_lot=rng.choice([-1, 0, 0, 3, 12, 30]),
                rounding_value=rng.choice([-1, 0, 1, 2, 5, 7]),
            )
            for index in range(rng.randint(0, 6))
        ]
        available = rng.randint(0, 80)
        expected = _enumerated_plan(available, requests)
        rng.shuffle(requests)

        shipped = allocate(available, requests)

        assert shipped == expected, (available, requests)
        assert sum(shipped.values()) <= available
