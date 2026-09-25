# Human Interface: агент-оператор финансового API

LangChain-агент (OpenAI), который по текстовому запросу пользователя вызывает
HTTP API сервиса учёта финансовых операций (`../money_service`) и печатает
ответ в фиксированном контракте:

```
Status: success | error
Action: <вызов инструмента>
Data: <результат API>
Errors: <если есть>
```

## Установка

```bash
uv venv --python 3.11
uv pip install -r requirements-dev.txt
cp .env.example .env   # заполнить OPENAI_API_KEY
```

## Запуск

```bash
# терминал 1: запустить API
cd ../money_service && flask --app app run

# терминал 2: агент
python main.py "запиши покупку продуктов на 5000"
```

Переменные окружения (`.env`):

| Переменная | Назначение | По умолчанию |
|---|---|---|
| `OPENAI_API_KEY` | ключ OpenAI (обязательно) | — |
| `OPENAI_MODEL` | модель | `gpt-4o-mini` |
| `OPENAI_BASE_URL` | опциональный OpenAI-совместимый эндпоинт | api.openai.com |
| `MONEY_SERVICE_BASE_URL` | адрес money_service | `http://127.0.0.1:5000` |

## Как это устроено

- `finance_tools.py` — 6 LangChain-tools (список категорий, CRUD операций, баланс);
  каждый делает явный HTTP-вызов через `requests` и всегда возвращает JSON-строку
  `{"ok": true, "data": ...}` / `{"ok": false, "error": ...}`. Ошибки API не ретраятся.
  Категория передаётся инструментам именем (`category_name`): Python сам резолвит его
  в `category_id` (точное/префиксное/нечёткое совпадение) и возвращает ошибку для
  несуществующей или неподходящей по типу категории — LLM не принимает решение о существовании категории.
- `money.py` — детерминированный парсер сумм: LLM передаёт сумму дословно строкой
  (`"5000"`, `"1 234,56"`), Python конвертирует в копейки для API.
  Разделитель с 1–2 цифрами на конце — десятичный; с 3 цифрами — групповой (`5.000` = 5000 ₽).
- `agent.py` — системный prompt (роль API-оператора, ограничения, правила вызова tools)
  и цикл tool-calling с лимитом итераций.
- `respond.py` — финальный контракт собирает код, а не LLM: Status/Action/Data/Errors.

## Тесты и линтинг

```bash
pytest tests/ -q
ruff check . && ruff format --check .
```
