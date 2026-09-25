# План изменений: CRUD для операций и баланс

## 1. Цель

Расширить API: операции можно создавать, получать по id, обновлять частично (PATCH)
и получать списком. Добавить эндпоинт текущего баланса: сумма приходных операций
минус сумма расходных.

## 2. Новые эндпоинты

| Метод | Путь | Успех | Ошибки |
| --- | --- | --- | --- |
| `GET` | `/operations` | `200` + JSON-список всех операций (порядок по `id`) | — |
| `GET` | `/operations/<id>` | `200` + JSON операции | `404` — операция не найдена |
| `PATCH` | `/operations/<id>` | `200` + JSON обновлённой операции | `400` — невалидное тело/поля, пустое тело; `404` — операция или категория не найдена; `400` — тип категории не совпадает с типом операции |
| `GET` | `/balance` | `200` + `{"balance": <int>}` | — |

Решения:

- обновление — частичное (`PATCH`): меняются только переданные поля
  (`type`, `amount`, `category_id`, `comment`); `id` и `created_at` неизменяемы;
- список без фильтров и пагинации;
- баланс в копейках (та же единица, что и `amount`), отрицательный допустим.

## 3. Изменения по файлам

### `app/repositories.py`

У `OperationRepository` добавить:

- `get_by_id(operation_id) -> Operation | None`
- `update(operation_id, **fields) -> Operation | None` — `None`, если операции нет
- `list_all() -> list[Operation]` — `order_by(Operation.id)`
- `balance() -> int` — SQL-агрегат одним запросом:
  `sum(case(income -> amount, else -amount))` через `func.coalesce(func.sum(...), 0)`,
  чтобы не выбирать все строки в Python

### `app/validators.py`

- вынести общие проверки: `_check_type`, `_check_amount`, `_check_category_id`, `_check_comment`;
- `validate_operation` переписать на этих хелперах (поведение и сообщения об ошибках сохраняются);
- добавить `validate_operation_update(data) -> dict`:
  - принимает только `type`, `amount`, `category_id`, `comment`;
  - поля опциональны, но при наличии проходят те же проверки;
  - пустое тело (ни одного изменяемого поля) → `ValidationError`;
  - `id` / `created_at` в теле → `ValidationError` (нельзя менять);
  - `comment: null` разрешён — очищает комментарий.

### `app/routes.py`

- общий хелпер `_category_type_error(category_repo, type_, category_id)`:
  `404` при отсутствии категории, `400` при несовпадении типов (используется и в `POST /operations`);
- `GET /operations` → список через `operation_repo.list_all()`;
- `GET /operations/<int:operation_id>` → `404`, если репозиторий вернул `None`;
- `PATCH /operations/<int:operation_id>`:
  1. разбор и валидация тела (`validate_operation_update`);
  2. загрузка операции → `404`;
  3. если меняются `type` или `category_id` — проверка новой пары тип/категория;
  4. `operation_repo.update(...)` → `200` с обновлённым JSON;
- `GET /balance` → `{"balance": operation_repo.balance()}`.

### `app/models.py`

Без изменений (схема та же).

### `tests/conftest.py`

Расширить `FakeOperationRepository`: `get_by_id`, `update`, `list_all`, `balance`
(unit-тесты остаются без обращения к БД).

### `tests/test_operations.py`

Unit-тесты (мок репозитория):

- `GET /operations/<id>`: успех и `404`;
- `GET /operations`: пустой список и несколько операций;
- `PATCH`: успех (`amount`/`comment`), неизменность `created_at`, смена `category_id`;
- `PATCH` → `400`: пустое тело, `amount <= 0`, неверный `type`, нестрогий тип `amount`,
  попытка изменить `id`/`created_at`;
- `PATCH` → `404`: операция не найдена, категория не найдена;
- `PATCH` → `400`: тип новой категории не совпадает с типом операции;
- `GET /balance`: нет операций → `0`, только приход → положительный, mixed → разность,
  преобладание расходов → отрицательный.

### `tests/test_integration.py`

На реальной in-memory SQLite: создание категорий и операций, `GET` по id, список,
`PATCH` (изменение суммы), корректность `GET /balance`, `404` для несуществующей операции.

### `README.md`

Дополнить раздел API новыми методами, кодами ответов и форматом `/balance`.

## 4. Проверки качества

```bash
pytest --cov=app          # покрытие app/ >= 80%
ruff check .
ruff format --check .
```
