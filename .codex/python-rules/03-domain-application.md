# 03. Application, DTO, порты и DI

Применяется к соответствующим ответственностям независимо от названия каталога.
Крупные области группируются в папки, небольшие отдельные роли — в файлы.

## Структура

```text
src/project_name/
  domain/                         # если есть предметная модель
  application/
    commands/
      order/create_order.py
    interactors/
      order/get_order.py
    dto/
      user/user.py
      order/new_order.py
      order/order.py
    ports/
      user/reader.py
      user/saver.py
      user/updater.py
      order/reader.py
      order/saver.py
      security/password_hasher.py
      committer.py
      clock.py
      id_generator.py
    errors.py
  infrastructure/
    gateways/
      user.py
      order.py
    db/
      models.py                   # или models/<entity>.py при росте
      committer.py
      rate_limiter.py             # если реализация использует БД
    security/
      password_hasher.py
      access_token_codec.py
    clock.py
    auth/
      handlers/registration/sign_up.py
      handlers/session/refresh.py
      tokens/issuer.py
  presentation/
  config.py
  ioc.py
  main.py
```

Это карта возможных мест, а не шаблон для создания всех папок. Если контекстов
несколько, такой набор может находиться внутри каждого контекста.

- Не создавай перегруженные `application/ports.py`, `dto.py`, `use_cases.py`,
  общий модуль всех gateways или один `security.py` для разных алгоритмов.
- User и session имеют собственные группы контрактов. Committer не становится
  частью SessionReader; пароли и токены не смешиваются с DB-session API.
- В `dto/` и `ports/` заводи папку для растущей области; мелкие независимые
  понятия оставляй в отдельных файлах корня. Не делай папку под каждое слово.
- Не оставляй пустую `interfaces/` и каталоги-заготовки. Пустой `__init__.py`
  как маркер Python-пакета допустим.
- Импортируй из определяющего модуля. Не сохраняй старый `use_cases.py` или
  `ports.py`, содержащий только импорты, чтобы не обновлять вызывающий код.
  Регистрация ORM-моделей для Alembic и явно спроектированный публичный API
  библиотеки имеют собственную цель; это не compatibility shims.

## DTO и отсутствие записи

- Используй `dataclass(slots=True)`, для неизменяемого DTO — `frozen=True`.
  В DTO нет доступа к БД, HTTP, вычисления политики и вызовов адаптеров.
- DTO для создания не содержит сгенерированную identity; DTO обновления содержит
  `<entity>_id`. DTO чтения описывает результат, а не ORM-жизненный цикл.
- Базовый контракт одиночного `get` gateway: существующий DTO чтения с пустыми
  полями при отсутствии записи. Не `None`, не `object`, не отдельный EmptyUser,
  не subclass для отсутствующего результата.

```python
from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True, kw_only=True)
class UserDTO:
    id: UUID | None = None
    email: str = ''
```

Найденный объект обязан иметь identity и необходимые данные. Потребитель проверяет
`user.id is None` и остальные обязательные поля перед дальнейшим действием.
`if user` не подходит: dataclass с пустыми полями остаётся truthy. Пустой DTO
нельзя превращать в principal, токен или валидную domain entity.

Этот контракт не распространяется на все nullable-значения в программе: Config,
необязательная дата и SQLAlchemy row могут возвращать `None`. Не ослабляй
инварианты rich domain ради пустого результата; для чтения используй свой DTO.

## Узкие порты

```python
from typing import Protocol
from uuid import UUID


class UserReader(Protocol):
    async def get_by_id(self, user_id: UUID) -> UserDTO: ...


class UserSaver(Protocol):
    async def save(self, user: UserDTO) -> None: ...
```

- Application зависит от минимально нужных Reader/Saver/Updater/Deleter ролей.
  Несколько методов одной связной роли допустимы; один интерфейс на весь storage — нет.
- Порты для application находятся в `application/ports/`. Чисто технический
  интерфейс, который нужен только infrastructure, можно оставить в её подсистеме;
  application не начинает импортировать его оттуда.
- Конкретный gateway наследует нужные роли напрямую:
  `class UserGateway(UserReader, UserSaver, UserUpdater): ...`.
  Не вводи `UserGatewayInterface` только для их объединения, дополнительный
  `Protocol` в реализации и `@override` на реализациях методов портов.
- Часы, ID, случайность, хэширование и внешние эффекты внедряются через контракты.
  Синхронный чистый генератор не делай async; I/O-порты отражают реальный I/O.

## Операции, ошибки и DI

- У Command/Interactor один публичный `__call__` и конкретная ответственность.
  Зависимости внедряются в `__init__`. Команда обычно возвращает None или ID;
  дополнительный DTO результата вводится при необходимости контракта, не ORM-объект.
- Commit вызывается на уровне согласованной операции через Committer/UnitOfWork,
  а не скрывается в каждом gateway. Успешный ответ об изменении отдаётся после commit.
- Чтение может передать пустой DTO выше; обязательное существование для бизнес-действия
  проверяется операцией с явной ошибкой. HTTP-статус выбирает presentation.
- Application errors группируй отдельно от framework errors; одинаковый тип ошибки
  не оправдывает одинаковое сообщение для разных нарушений.
- DI связывается в одном composition root. Pools/settings/clients имеют lifecycle
  приложения, DB session — lifecycle запроса, зависимые handlers — тот же scope.
- При Dishka одну реализацию нескольких портов регистрируй через `AnyOf[...]`;
  нельзя случайно получить три разных gateway/session вместо одного объекта запроса.
- Не добавляй DI-контейнер в domain или service locator в каждую функцию.
  Для маленького CLI достаточно явного создания зависимостей в точке входа.
