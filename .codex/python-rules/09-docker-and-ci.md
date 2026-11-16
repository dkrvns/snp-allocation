# 09. Docker, локальный запуск и CI/CD

Применяется к запуску приложения, сервисам, образам и pipeline.

## Локальное окружение

- По умолчанию приложение, БД, миграции, dependency management и проверки
  выполняются в Docker. Не запускай host Python/uvicorn/PostgreSQL как обходной
  вариант при недоступности engine или mounts.
- Чтение и редактирование исходников на хосте разрешены. Временные утилиты работы
  с файлами не становятся host runtime приложения. Проверки самого проекта — в контейнере.
- Перед стартом проверь Docker context, engine, текущие сервисы и занятые порты.
  Не останавливай соседние проекты. Если Docker недоступен, исправь доступный
  runtime в разрешённом объёме или сообщи причину, не симулируй успешный старт.
- Если VM не поддерживает bind mounts, используй build context или `docker cp`.
  Не предполагается, что host filesystem автоматически виден внутри контейнера.
- Для локального UI публикуй нужный порт на loopback. DB/SMTP, доступные только
  сервисам Compose, обычно не нуждаются в host-портах.
- При запросе остановить проект останови его API, frontend, БД, почту и workers.
  Сохрани named volumes. `down --volumes` применяется только к подтверждённо
  одноразовому тестовому окружению, не к рабочим данным.

## Сборка и runtime

- Dev/test и runtime — разные targets. Зависимости устанавливаются по `uv.lock`;
  tools тестирования не входят в runtime. Layer с зависимостями кешируется
  отдельно от исходников.
- Не копируй `.env`, ключи, dumps, host venv, caches, `.git` и frontend dependencies
  в Python image. У mixed-проекта frontend имеет отдельный build context.
- Фиксируй проверенные версии образов/uv, для release — проверяй digest.
  Изменяемый tag не является гарантией одинаковой сборки завтра.
- Runtime работает non-root. Его запуск не должен переустанавливать зависимости
  в root-owned `.venv`: используй `UV_NO_SYNC=1` или `uv run --no-sync` после
  успешной установки при сборке. Не исправляй ошибку прав запуском API от root.
- Применение миграций — отдельный шаг перед API. При нескольких replicas
  не запускай конкурирующую миграцию в каждом worker без координации.
- `depends_on` использует health/completion conditions. Проверяй код выхода
  миграции, реальную доступность API и важный пользовательский путь, не только
  факт создания контейнера.

Пример targets для Debian-based Python image. `PYTHON_IMAGE` и `UV_IMAGE`
передаются при сборке с выбранными проверенными tags/digests. Имена пакета и
копируемые metadata-файлы адаптируются под проект; миграции при наличии тоже
нужно включить в runtime image.

```dockerfile
ARG PYTHON_IMAGE
ARG UV_IMAGE
FROM ${UV_IMAGE} AS uv_tool
FROM ${PYTHON_IMAGE} AS base
COPY --from=uv_tool /uv /uvx /usr/local/bin/
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never
WORKDIR /app
COPY pyproject.toml uv.lock ./

FROM base AS development
RUN uv sync --locked --no-install-project
COPY . .
RUN uv sync --locked
CMD ["uv", "run", "pytest"]

FROM base AS runtime
RUN uv sync --locked --no-dev --no-install-project
COPY src ./src
COPY README.md ./
RUN uv sync --locked --no-dev --no-editable \
    && useradd --uid 10001 --create-home app
ENV UV_NO_SYNC=1
USER 10001
CMD ["uv", "run", "--no-dev", "python", "-m", "project_name"]
```

UID в примере не универсален. Read-only/non-root startup проверяется на реально
собранном образе, включая миграции и платформу CI; успешный dev target этого не доказывает.

## Изоляция проверок

- У тестов отдельные Compose project/network, БД, почта, credentials и одноразовые
  volumes. Production `.env` не копируется в тестовый запуск.
- Не публикуй host-порты CI-сервисов. Для Compose override проверь итоговый merge:
  пустой обычный список не всегда удаляет унаследованные ports. Используй подходящий
  reset/override-механизм поддерживаемой версии Compose и проверь эффективный config.
- Не выводи полный effective config с секретами в лог. Проверка может извлечь
  только нужные безопасные поля, например отсутствие published ports.
- Cleanup выполняется всегда, включая ошибку и отмену. Он затрагивает только
  ресурсы собственного тестового проекта. Main/dev сервисы сохраняют состояние,
  запрошенное пользователем: остановленный сервер не запускается обратно после теста.
- Для image scanner не монтируй Docker socket без необходимости. Возможен экспорт
  image archive и проверка в отдельном контейнере без доступа к engine.

## GitHub Actions

- Явно настрой события: push в согласованные ветки, PR с базой `master`/`main`.
  По умолчанию push рабочей ветки тоже проверяется. Не путай head PR с его base.
- Job permissions минимальны, обычно `contents: read`. Не используй
  `pull_request_target` для выполнения недоверенного кода с secrets.
- Добавь timeouts и concurrency для устаревших запусков; группы push и PR
  не должны случайно отменять друг друга, если нужно проверить оба события.
- Python job: сборка dev target, Ruff, mypy, pytest с реальными тестовыми сервисами,
  dependency audit. Frontend job и browser job добавляй при наличии frontend.
- Browser job собирает и поднимает настоящий runtime, применяет миграции,
  дожидается readiness и запускает пользовательский сценарий с тестовыми данными.
- Auth secret генерируется одноразово, маскируется до диагностического вывода,
  передаётся только нужным контейнерам и не попадает в image/артефакт.
- При падении доступны безопасные startup logs API/migrations/frontend;
  очистка следует после диагностики. Не складывай credentials и request bodies
  в безусловно публикуемый лог или browser trace.
- Проверяй workflow через actionlint и реальные удалённые runs. Если локально
  зелёный код упал на runner, изучи платформу, image и runtime permissions.

## Доставка и завершение

Сборка, упаковка образов в artifact, публикация registry и deployment — разные
действия. Указывай, какое из них настроено. Delivery/release выполняется после
успеха нужных jobs и на разрешённом событии доверенной ветки; PR не публикует
production-артефакт с расширенными правами. Срок хранения и версия артефакта явные.

Не выдумывай deployment target, credentials и разрешение на публичную публикацию.
Если задан только CI, так и сообщи. После push проверь его checks и checks PR;
старый зелёный run не является результатом для нового HEAD.
