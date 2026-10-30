import random
import time
from fractions import Fraction

import pytest

from snp_allocation import AllocationInputError, Request, allocate


def _request(
    request_id: str,
    priority: int,
    demand_qty: int,
    min_lot: int = 0,
    rounding_value: int = 1,
) -> Request:
    return Request(
        request_id=request_id,
        dest_location=f'DC_{request_id}',
        priority=priority,
        demand_qty=demand_qty,
        min_lot=min_lot,
        rounding_value=rounding_value,
    )


def test_allocate_proportional_to_demand() -> None:
    """Фиксирует: внутри одного приоритета объём делится пропорционально спросу:
    спрос 30 и 10 при остатке 20 даёт 15 и 5, у обоих по 50 %.
    Сломается: при делении поровну в штуках (10 и 10) малая заявка получит
    100 %, а крупная только 33 %.
    """
    requests = [_request('A', 1, 30), _request('B', 1, 10)]

    shipped = allocate(20, requests)

    assert shipped == {'A': 15, 'B': 5}


def test_allocate_round_up_does_not_take_from_lower_priority_demand() -> None:
    """Фиксирует: если шаг округления вверх не помещается (A нужно ещё 25, а
    осталось 20), остаток не пропадает и уходит следующему приоритету: B = 20.
    Сломается: если остаток придерживать под докругление A, B получит 0,
    а 20 штук останутся лежать на складе.
    """
    requests = [_request('A', 1, 40, rounding_value=25), _request('B', 2, 20)]

    shipped = allocate(45, requests)

    assert shipped == {'A': 25, 'B': 20}


def test_allocate_round_up_covers_higher_priority_before_lower() -> None:
    """Фиксирует: докругление старшего приоритета делается до перехода к младшему:
    при остатке 50 A (спрос 40, кратность 25) получает 50, B с приоритетом 2 — 0.
    Сломается: если докруглять после всех приоритетов, B заберёт 25, а A
    останется с 25 из 40, хотя её недостача важнее спроса B.
    """
    requests = [_request('A', 1, 40, rounding_value=25), _request('B', 2, 25)]

    shipped = allocate(50, requests)

    assert shipped == {'A': 50, 'B': 0}


def test_allocate_skips_lot_that_does_not_fit_and_continues() -> None:
    """Фиксирует: заявка с крупной минимальной партией получает её, пока партия
    помещается: при остатке 70 A (min_lot 60) получает 60, B — оставшиеся 10.
    Сломается: если сначала раздать пропорциональные доли (по 35), партия A
    уже не влезет, A получит 0, а B все 70; так работала первая версия.
    """
    requests = [_request('A', 1, 100, min_lot=60), _request('B', 1, 100)]

    shipped = allocate(70, requests)

    assert shipped == {'A': 60, 'B': 10}


def _reference_level(requests: list[Request], budget: int) -> dict[str, int]:
    shipped = {r.request_id: 0 for r in requests}

    def fill_rate(r: Request) -> tuple[Fraction, str]:
        return Fraction(shipped[r.request_id], r.demand_qty), r.request_id

    def next_qty(r: Request) -> int:
        step = r.rounding_value or 1
        current = shipped[r.request_id]
        return current + step if current else max(step, -(-r.min_lot // step) * step)

    active = list(requests)
    while active:
        r = min(active, key=fill_rate)
        target, current = next_qty(r), shipped[r.request_id]
        if target > r.demand_qty or target - current > budget:
            active.remove(r)
            continue
        shipped[r.request_id] = target
        budget -= target - current

    for r in sorted(requests, key=fill_rate):
        target, current = next_qty(r), shipped[r.request_id]
        if current < r.demand_qty and target - current <= budget:
            shipped[r.request_id] = target
            budget -= target - current
    return shipped


def test_allocate_matches_step_by_step_reference() -> None:
    """Фиксирует: на 300 случайных кейсах ускоренный алгоритм (бинарный поиск по
    проценту покрытия) даёт ровно тот же план, что простая пошаговая раздача.
    Сломается: план начнёт зависеть от оптимизации, а не от правила; первой
    обычно страдает заявка с крупным min_lot.
    """
    rng = random.Random(7)
    for _ in range(300):
        requests = [
            _request(
                f'R{i}',
                1,
                rng.randint(1, 120),
                min_lot=rng.choice([0, 0, 15, 40, 90]),
                rounding_value=rng.choice([1, 5, 7, 10, 25]),
            )
            for i in range(rng.randint(1, 6))
        ]
        budget = rng.randint(0, sum(r.demand_qty for r in requests) + 50)
        expected = _reference_level(requests, budget)

        shipped = allocate(budget, requests)

        assert shipped == expected, (budget, requests)


def test_allocate_zero_available() -> None:
    """Фиксирует: при пустом складе все заявки получают 0 и при этом
    присутствуют в результате.
    Сломается: если пропускать заявки без отгрузки, вывод и любой код, который
    читает план по request_id, упадут с KeyError.
    """
    requests = [_request('A', 1, 10), _request('B', 2, 10)]

    shipped = allocate(0, requests)

    assert shipped == {'A': 0, 'B': 0}


def test_allocate_large_volume_is_fast() -> None:
    """Фиксирует: 200 заявок на 10^11 штук распределяются полностью меньше чем
    за секунду: время зависит от числа заявок, а не от объёма.
    Сломается: если раздавать по одной штуке, такой кейс будет считаться
    часами, и ночной пересчёт 5 млн кейсов не уложится в окно.
    """
    requests = [_request(f'R{i:03}', 1, 10**9 + i) for i in range(200)]
    started = time.perf_counter()

    shipped = allocate(10**11 - 7, requests)

    assert sum(shipped.values()) == 10**11 - 7
    assert time.perf_counter() - started < 1


def test_allocate_negative_available() -> None:
    """Фиксирует: отрицательный остаток на складе — ошибка AllocationInputError.
    Сломается: если молча считать его нулём, кривые данные дадут пустой план,
    и никто не узнает о проблеме в источнике.
    """
    with pytest.raises(AllocationInputError, match='available_qty'):
        allocate(-1, [_request('A', 1, 10)])


def test_allocate_duplicate_request_id() -> None:
    """Фиксирует: два одинаковых request_id в кейсе — ошибка AllocationInputError.
    Сломается: результат — словарь по request_id, отгрузка одной заявки
    перезапишет другую, и сумма плана перестанет сходиться.
    """
    requests = [_request('A', 1, 10), _request('A', 2, 10)]

    with pytest.raises(AllocationInputError, match='unique'):
        allocate(10, requests)
