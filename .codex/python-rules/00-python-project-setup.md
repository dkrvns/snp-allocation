# 00. Окружение и инструменты

Применяется к Python-проекту и его конфигурации. Docker-команды и CI см. в разделе 09.

## Python и uv

- Для нового проекта базовая версия — Python 3.14: `.python-version` содержит
  `3.14`, `requires-python = ">=3.14"`. Совместимость библиотеки с более старыми
  версиями и изменение версии существующего проекта согласовываются отдельно.
- Используй uv: создание проекта — `uv init --app` или `uv init --package`,
  зависимости — `uv add/remove`, lockfile — `uv lock`, установка — `uv sync`,
  команды — `uv run`. Выполняй их в dev-контейнере. Python интерпретатор берётся
  из образа, а не устанавливается на хост ради запуска проекта.
- Не добавляй параллельный менеджер зависимостей, requirements.txt, setup.py
  или ручную активацию venv. Существующий другой workflow сначала исследуй.
- `uv.lock` хранится в Git, CI/сборка используют `uv sync --locked`.
  Не редактируй вручную списки зависимостей; меняй их через uv с обновлением lockfile.
- Ruff, mypy, pytest и другие dev tools размещаются в dev dependency group.
  Добавляй только реально используемые инструменты. Extras указывай явно,
  например `sqlalchemy[asyncio]`; фреймворк не становится обязательным для всех проектов.

## Одна конфигурация

Настройки Python-инструментов храни в `pyproject.toml`. Не дублируй их в
`pytest.ini`, `mypy.ini`, `.ruff.toml` или отдельном pyrightconfig без причины.
Согласуй Python-версию runtime, Ruff, mypy и редактора.

```toml
[project]
name = "project-name"
version = "0.1.0"
requires-python = ">=3.14"
dependencies = []

[dependency-groups]
dev = []

[tool.ruff]
target-version = "py314"
line-length = 88
src = ["src", "tests"]
extend-exclude = ["migrations"]

[tool.ruff.lint]
select = ["E", "W", "F", "I", "B", "C4", "UP", "SIM", "RUF", "ASYNC", "PT"]

[tool.ruff.lint.isort]
known-first-party = ["project_name"]

[tool.ruff.format]
quote-style = "single"
line-ending = "lf"

[tool.mypy]
python_version = "3.14"
strict = true
files = ["src"]

[tool.pyright]
pythonVersion = "3.14"

[tool.pytest]
testpaths = ["tests"]
asyncio_mode = "auto"
asyncio_default_fixture_loop_scope = "session"
asyncio_default_test_loop_scope = "session"
```

Это стартовый пример конфигурации инструментов, не полный packaging manifest.
Добавь build-system и настройки выбранного uv app/package при создании проекта.
Dev group заполняется командами `uv add --dev`; пустой список не означает,
что инструменты уже установлены. Раздел `[tool.pytest]` предназначен для pytest 9+;
asyncio-настройки нужны при установленном pytest-asyncio и асинхронных тестах.

- Глобальные lint ignores требуют объяснения. Для конкретной строки допустим
  узкий `noqa` с кодом и причиной, не отключение проверки всего проекта.
- При диагностике нового синтаксиса сначала проверь target version и выбранный
  интерпретатор Pylance. При необходимости перезапусти language server.
  Не понижай Python-версию проекта ради предупреждения редактора.
- Settings читаются из окружения через отдельный Config; `.env` — локальный файл.
  В Git хранится полный `.env.example` без рабочих секретов. В тестовом окружении
  конфигурация задаётся отдельно, не наследуется случайно от рабочей БД.

## Проверки завершения

Для Python-изменений выполни в Docker Ruff format/check, проверку типов и
релевантные pytest. Перед коммитом полный набор обязателен, если он задан проектом.
При запрете на изменение существующих тестов запускай форматтер для разрешённых
файлов, а остальные проверяй через `ruff format --check`; не применяй `--fix .`
без разбора. Ошибки, недоступные сервисы и непройденные проверки явно сообщаются.
Для чисто документационной задачи проверяются документы и затронутые примеры.
