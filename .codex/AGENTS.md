# Индекс правил Python

Правила находятся в [python-rules/](python-rules/) относительно этого файла.
Читай целиком применимые файлы. Для сквозной задачи используй несколько разделов.
При недоступности файла сообщи об этом; не утверждай, что прочитал его.

| Работа | Разделы |
| --- | --- |
| Python: окружение и инструменты | [00 — Окружение](python-rules/00-python-project-setup.md) |
| Чтение и изменение Python-кода | [01 — Стиль](python-rules/01-python-code-style.md) |
| Границы слоёв и выбор архитектуры | [02 — Архитектура](python-rules/02-clean-architecture.md) |
| DTO, порты, commands/interactors, DI | [03 — Application и контракты](python-rules/03-domain-application.md) |
| БД, gateways, транзакции, миграции | [04 — База данных](python-rules/04-infrastructure-db.md) |
| HTTP, FastAPI, схемы и startup | [05 — Presentation](python-rules/05-presentation-api.md) |
| Новые тесты и ревью существующих | [06 — Тестирование](python-rules/06-testing.md) |
| Любые Git-действия, коммиты, push и PR | [07 — Git](python-rules/07-git-workflow.mdc) |
| Код, зависимости, конфигурация и review | [08 — Качество и безопасность](python-rules/08-code-review-security.md) |
| Docker, локальные сервисы, CI/CD | [09 — Runtime и CI](python-rules/09-docker-and-ci.md) |
| Аутентификация, SMTP и внешние эффекты | [10 — Технические подсистемы](python-rules/10-auth-and-integrations.md) |

Базовый стек — Python 3.14 и uv, запуск и проверки — в Docker. Указанный в
конкретном проекте стек или версия изменяются только в рамках согласованной задачи.
Наличие раздела не требует устанавливать соответствующий фреймворк или сервис.
Для Markdown-only задачи выполняются проверки документации из README;
запуск несуществующего pytest-проекта не требуется.
