# SNP Heuristic — распределение дефицита

Элементарная операция SNP Heuristic: распределение доступного объёма одной позиции
в одном периоде между заявками с учётом приоритета, `min_lot` и `rounding_value`.
Правило и обоснование решений — в [REPORT.md](REPORT.md).

Нужен только [uv](https://docs.astral.sh/uv/); Python 3.14 uv поставит сам.

## Запуск

```bash
uv run python -m snp_allocation
```

По умолчанию читаются `data/supply.csv` и `data/requests.csv`; другие файлы —
`--supply <path> --requests <path>`. Для каждого кейса выводится, какая заявка
сколько получила, процент покрытия спроса, нераспределённый остаток и замечания
к данным (строки с `!`).

## Тесты и проверки

```bash
uv run pytest
uv run ruff format --check .
uv run ruff check .
```

## Структура

| Файл | Что внутри |
|---|---|
| `src/snp_allocation/allocation.py` | ядро: `Request`, `allocate()` (129 строк) |
| `src/snp_allocation/diagnostics.py` | замечания к данным заявки |
| `src/snp_allocation/csv_io.py` | чтение CSV в кейсы |
| `src/snp_allocation/__main__.py` | точка входа и вывод |
| `tests/csv_cases_test.py` | кейсы из CSV, жёсткие ограничения, независимость от порядка строк |
| `tests/allocation_test.py` | собственные сценарии и сверка с эталонным пошаговым алгоритмом |
