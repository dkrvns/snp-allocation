# SNP Heuristic — распределение дефицита

Элементарная операция SNP Heuristic: распределение доступного объёма одной позиции
в одном периоде между заявками с учётом приоритета, `min_lot` и `rounding_value`.
Правило и обоснование решений — в [REPORT.md](REPORT.md).

Нужен Docker. Python 3.14 и [uv](https://docs.astral.sh/uv/) находятся в образе;
на хосте устанавливать Python и зависимости не требуется.

## Запуск

```bash
docker build --target runtime -t snp-allocation:local .
docker run --rm snp-allocation:local
```

По умолчанию читаются `data/supply.csv` и `data/requests.csv`; другие файлы —
`--supply <path> --requests <path>`. Пользовательские файлы можно скопировать
в контейнер; если Docker поддерживает bind mounts, передать каталог так:

```bash
docker run --rm -v "$PWD/data:/input:ro" snp-allocation:local \
  --supply /input/supply.csv --requests /input/requests.csv
```

Для каждого кейса выводится, какая заявка
сколько получила, процент покрытия спроса, нераспределённый остаток и замечания
к данным (строки с `!`).

CSV читается как UTF-8 с необязательным BOM. Заголовки должны содержать колонки
из примеров в `data/`; их порядок произвольный, дополнительные колонки разрешены.
Повторные заголовки, пустые обязательные поля, неполные или лишние поля строки,
нецелые количества и повреждённые кавычки отклоняются с именем файла и номером
строки. Пустые строки пропускаются. При ошибке входных данных CLI завершается
с кодом 2 и сообщением в stderr, без частично напечатанного плана.

## Тесты и проверки

```bash
docker build --target development -t snp-allocation:dev .
docker run --rm snp-allocation:dev uv run --no-sync ruff format --check .
docker run --rm snp-allocation:dev uv run --no-sync ruff check .
docker run --rm snp-allocation:dev uv run --no-sync mypy
docker run --rm snp-allocation:dev
```

Последняя команда запускает полный pytest. После правок исходников образ нужно
пересобрать. Development-образ содержит инструменты проверок, runtime-образ —
только приложение и примеры CSV, работает без root и без установки зависимостей
при запуске. Зависимости фиксируются в `uv.lock`.

Правила разработки подключены в [AGENTS.md](AGENTS.md) и [.codex/](.codex/AGENTS.md).
Сила тестов и результаты проверки намеренными ошибками — в
[TEST_REVIEW.md](TEST_REVIEW.md).

## Структура

| Файл | Что внутри |
|---|---|
| `src/snp_allocation/allocation.py` | чистое ядро: `Request`, `allocate()` и правила партий |
| `src/snp_allocation/diagnostics.py` | замечания к данным заявки |
| `src/snp_allocation/csv_io.py` | чтение CSV в кейсы |
| `src/snp_allocation/__main__.py` | точка входа и вывод |
| `tests/csv_cases_test.py` | кейсы из CSV, жёсткие ограничения, независимость от порядка строк |
| `tests/allocation_test.py` | собственные сценарии и сверка с эталонным пошаговым алгоритмом |
| `tests/csv_io_test.py` | формат CSV, диагностика ошибок, BOM и неизвестные кейсы |
| `tests/cli_test.py` | вывод CLI и отказ на ошибках без частичного плана |
| `tests/*_contract_test.py` | границы контрактов, независимый эталон и реальные CLI-запуски |
| `tests/diagnostics_test.py` | полные списки предупреждений и граничные значения |
| `Dockerfile` | отдельные development и runtime targets |
