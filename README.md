# Финансовый сервис + агент (homework4)

Репозиторий объединяет два сервиса:

| Сервис | Что это | Подробнее |
|---|---|---|
| [`money_service`](money_service/README.md) | Flask API учёта финансовых операций (категории, операции, баланс) на in-memory SQLite | [README](money_service/README.md) |
| [`human_interface`](human_interface/README.md) | LangChain-агент (OpenAI): по текстовому запросу вызывает HTTP API `money_service` и печатает ответ в фиксированном контракте | [README](human_interface/README.md) |

## Как они связаны

```
пользователь ("запиши покупку продуктов на 5000")
        │
        ▼
human_interface  ── HTTP (http://127.0.0.1:5000) ──►  money_service  ──►  SQLite in-memory
   LangChain-агент                                       Flask API
```

`human_interface` обращается к `money_service` только через его HTTP API
(`GET/POST /categories`, `GET/POST/PATCH /operations`, `GET /balance`) — зависимости между пакетами на уровне кода нет, связь только по HTTP.

## Быстрый запуск

Оба сервиса — Python 3.11+, используется `uv`.

```bash
# терминал 1: API-сервис
cd money_service
uv venv --python 3.11 && uv pip install -e ".[dev]"
uv run flask --app app run                      # http://127.0.0.1:5000

# терминал 2: агент
cd human_interface
uv venv --python 3.11 && uv pip install -r requirements-dev.txt
cp .env.example .env                     # заполнить OPENAI_API_KEY
uv run python main.py "запиши покупку продуктов на 5000"
```

Адрес API задаётся переменной `MONEY_SERVICE_BASE_URL` в `.env` агента
(по умолчанию `http://127.0.0.1:5000` — совпадает с портом Flask по умолчанию).

## Тесты и линтинг

```bash
# money_service
cd money_service && pytest --cov=app && ruff check .

# human_interface
cd human_interface && pytest tests/ -q && ruff check .
```

## Детали

- API-контракт `money_service` (эндпоинты, коды ответов, валидация): [money_service/README.md](money_service/README.md)
- Устройство агента (tools, парсер сумм, контракт ответа `Status/Action/Data/Errors`, переменные окружения): [human_interface/README.md](human_interface/README.md)
