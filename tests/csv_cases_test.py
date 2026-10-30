import random
from pathlib import Path

import pytest

from snp_allocation import allocate
from snp_allocation.csv_io import Case, load_cases

DATA_DIR = Path(__file__).resolve().parents[1] / 'data'

EXPECTED = {
    'CASE_01': {'R-101': 50, 'R-102': 25, 'R-103': 25},
    'CASE_02': {'R-201': 40, 'R-202': 30, 'R-203': 30, 'R-204': 0},
    'CASE_03': {'R-301': 0, 'R-302': 0, 'R-303': 30, 'R-304': 30},
    'CASE_04': {'R-401': 20, 'R-402': 20, 'R-403': 19, 'R-404': 19, 'R-405': 19},
    'CASE_05': {'R-501': 50, 'R-502': 40, 'R-503': 10},
    'CASE_06': {'R-601': 100, 'R-602': 0, 'R-603': 84},
    'CASE_07': {'R-701': 100, 'R-702': 0, 'R-703': 0},
}


def _cases() -> dict[str, Case]:
    cases, _ = load_cases(DATA_DIR / 'supply.csv', DATA_DIR / 'requests.csv')
    return {case.case_id: case for case in cases}


@pytest.mark.parametrize('case_id', EXPECTED)
def test_allocate_csv_case(case_id: str) -> None:
    """Фиксирует: для каждого кейса из data/ план совпадает с ответом из EXPECTED,
    посчитанным вручную по выбранному правилу.
    Сломается: любое изменение правила (приоритет, округление, ничьи) поменяет
    план хотя бы в одном кейсе, и тест покажет, в каком именно.
    """
    case = _cases()[case_id]

    shipped = allocate(case.available_qty, case.requests)

    assert shipped == EXPECTED[case_id]


@pytest.mark.parametrize('case_id', EXPECTED)
def test_allocate_csv_case_within_available(case_id: str) -> None:
    """Фиксирует: сумма отгрузок по кейсу не больше available_qty
    (обязательное требование 1).
    Сломается: план начнёт отгружать товар, которого физически нет на складе,
    и исполнить его будет невозможно.
    """
    case = _cases()[case_id]

    shipped = allocate(case.available_qty, case.requests)

    assert sum(shipped.values()) <= case.available_qty


@pytest.mark.parametrize('case_id', EXPECTED)
def test_allocate_csv_case_respects_lots(case_id: str) -> None:
    """Фиксирует: каждая отгрузка либо 0, либо не меньше min_lot и кратна
    rounding_value; кратность 0 считается как 1 (обязательное требование 2).
    Сломается: склад не сможет собрать такую отгрузку: партия меньше
    минимальной или не целое число упаковок.
    """
    case = _cases()[case_id]

    shipped = allocate(case.available_qty, case.requests)

    for r in case.requests:
        qty = shipped[r.request_id]
        step = r.rounding_value or 1
        assert qty == 0 or (qty >= r.min_lot and qty % step == 0)


@pytest.mark.parametrize('case_id', EXPECTED)
def test_allocate_csv_case_ignores_row_order(case_id: str) -> None:
    """Фиксирует: перемешанные заявки дают тот же план, ничьи решаются по
    request_id, а не по позиции строки (обязательное требование 3).
    Сломается: повторный расчёт на тех же данных из БД может дать другой план;
    например, в CASE_04 лишние 2 штуки уйдут другим DC.
    """
    case = _cases()[case_id]
    shuffled = case.requests.copy()
    random.Random(42).shuffle(shuffled)

    shipped = allocate(case.available_qty, shuffled)

    assert shipped == allocate(case.available_qty, case.requests)
