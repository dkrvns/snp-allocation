import heapq
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from fractions import Fraction
from itertools import groupby
from typing import Self


@dataclass(frozen=True, slots=True)
class Request:
    request_id: str
    dest_location: str
    priority: int
    demand_qty: int
    min_lot: int = 0
    rounding_value: int = 0


class AllocationInputError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class Lot:
    step: int
    first: int

    @classmethod
    def of(cls, request: Request) -> Self:
        step = request.rounding_value or 1
        return cls(step=step, first=max(step, _ceil_to(request.min_lot, step)))

    def floor(self, qty: int) -> int:
        return 0 if qty < self.first else qty // self.step * self.step

    def ceil(self, qty: int) -> int:
        return max(self.first, _ceil_to(qty, self.step))

    def next_after(self, qty: int) -> int:
        return self.first if qty == 0 else qty + self.step


def _ceil_to(qty: int, step: int) -> int:
    return -(-qty // step) * step


def is_valid(request: Request) -> bool:
    return (
        request.priority >= 1
        and min(request.demand_qty, request.min_lot, request.rounding_value) >= 0
    )


def allocate(available_qty: int, requests: Iterable[Request]) -> dict[str, int]:
    ordered = sorted(requests, key=lambda r: r.request_id)
    if available_qty < 0:
        raise AllocationInputError('available_qty must be non-negative')
    if len({r.request_id for r in ordered}) != len(ordered):
        raise AllocationInputError('request_id must be unique')

    shipped = dict.fromkeys((r.request_id for r in ordered), 0)
    eligible = [r for r in ordered if is_valid(r) and r.demand_qty > 0]
    remaining = available_qty
    by_priority = sorted(eligible, key=lambda r: r.priority)
    for _, group in groupby(by_priority, key=lambda r: r.priority):
        level = list(group)
        remaining = _fill_demand(level, remaining, shipped)
        remaining = _round_up(level, remaining, shipped)
    return shipped


_FILL_BITS = 64
_FILL_SCALE = 1 << _FILL_BITS


def _fill_rate(request: Request, shipped: dict[str, int]) -> Fraction:
    return Fraction(shipped[request.request_id], request.demand_qty)


def _qty_at_fill(request: Request, cap: int, level_x: int) -> int:
    target = -(-request.demand_qty * level_x >> _FILL_BITS)
    if target > cap:
        return cap
    return 0 if target == 0 else Lot.of(request).ceil(target)


def _fill_demand(level: Sequence[Request], budget: int, shipped: dict[str, int]) -> int:
    lots = {r.request_id: Lot.of(r) for r in level}
    caps = {r.request_id: lots[r.request_id].floor(r.demand_qty) for r in level}
    if sum(caps.values()) <= budget:
        shipped.update(caps)
        return budget - sum(caps.values())

    def state_at(x: int) -> dict[str, int]:
        return {r.request_id: _qty_at_fill(r, caps[r.request_id], x) for r in level}

    low, high = 0, _FILL_SCALE
    while low < high:
        mid = (low + high + 1) // 2
        if sum(state_at(mid).values()) <= budget:
            low = mid
        else:
            high = mid - 1
    shipped.update(state_at(low))
    remaining = budget - sum(shipped[r.request_id] for r in level)

    heap = [(_fill_rate(r, shipped), r.request_id, r) for r in level]
    heapq.heapify(heap)
    while heap:
        _, request_id, request = heapq.heappop(heap)
        current = shipped[request_id]
        target = lots[request_id].next_after(current)
        if target > caps[request_id] or target - current > remaining:
            continue
        shipped[request_id] = target
        remaining -= target - current
        heapq.heappush(heap, (_fill_rate(request, shipped), request_id, request))
    return remaining


def _round_up(level: Sequence[Request], budget: int, shipped: dict[str, int]) -> int:
    remaining = budget
    for r in sorted(level, key=lambda r: (_fill_rate(r, shipped), r.request_id)):
        current = shipped[r.request_id]
        target = Lot.of(r).ceil(r.demand_qty)
        if current < r.demand_qty and target - current <= remaining:
            shipped[r.request_id] = target
            remaining -= target - current
    return remaining
