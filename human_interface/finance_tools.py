from __future__ import annotations

import difflib
import json

import requests
from langchain_core.tools import tool

from money import AmountParseError, to_kopecks

TIMEOUT_SECONDS = 10
FUZZY_CUTOFF = 0.75


def _request(
    session: requests.Session,
    base_url: str,
    method: str,
    path: str,
    payload: dict | None = None,
) -> dict:
    try:
        url = f"{base_url}{path}"
        response = session.request(method, url, json=payload, timeout=TIMEOUT_SECONDS)
    except requests.RequestException as exc:
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}

    try:
        body = response.json()
    except ValueError:
        body = None

    if 200 <= response.status_code < 300:
        return {"ok": True, "data": body}

    error = body.get("error") if isinstance(body, dict) else None
    return {"ok": False, "error": error or f"HTTP {response.status_code}"}


def _resolve_category(session: requests.Session, base_url: str, name: str) -> dict:
    result = _request(session, base_url, "GET", "/categories")
    if not result["ok"]:
        return result

    categories = result["data"] or []
    norm = name.strip().lower()

    candidates = [c for c in categories if c["name"].strip().lower() == norm]
    if not candidates:
        candidates = [
            c
            for c in categories
            if (low := c["name"].strip().lower()).startswith(norm) or norm.startswith(low)
        ]
    if not candidates:
        by_name = {c["name"].strip().lower(): c for c in categories}
        candidates = [
            by_name[key]
            for key in difflib.get_close_matches(norm, list(by_name), n=3, cutoff=FUZZY_CUTOFF)
        ]

    if not candidates:
        return {"ok": False, "error": f"unknown category {name!r}"}
    if len(candidates) > 1:
        names = ", ".join(c["name"] for c in candidates)
        return {"ok": False, "error": f"ambiguous category {name!r}: {names}"}
    return {"ok": True, "data": candidates[0]}


def build_tools(base_url: str):
    session = requests.Session()

    def _json(payload: dict) -> str:
        return json.dumps(payload, ensure_ascii=False)

    @tool
    def list_categories() -> str:
        """Список всех категорий financial сервиса: [{"id", "name", "type"}].
        type категории: income или expense. Использовать для информационных запросов;
        для create_operation/update_operation не обязателен — там категория передаётся именем."""
        return _json(_request(session, base_url, "GET", "/categories"))

    @tool
    def create_operation(
        type: str,
        amount: str,
        category_name: str,
        comment: str | None = None,
    ) -> str:
        """Создать финансовую операцию.
        type: income (приход) или expense (расход).
        amount: сумма строкой как сказал пользователь ("5000", "1 234,56") —
          конвертация в копейки выполняется автоматически.
        category_name: название категории из запроса пользователя (именительный падеж,
          единственное число) — инструмент сам найдёт категорию и вернёт ошибку,
          если категории нет или её тип не совпадает с type."""
        try:
            amount_kopecks = to_kopecks(amount)
        except AmountParseError as exc:
            return _json({"ok": False, "error": str(exc)})
        resolved = _resolve_category(session, base_url, category_name)
        if not resolved["ok"]:
            return _json(resolved)
        category = resolved["data"]
        if category["type"] != type:
            mismatch = (
                f"category '{category['name']}' has type '{category['type']}', "
                f"operation type is '{type}'"
            )
            return _json({"ok": False, "error": mismatch})
        payload = {"type": type, "amount": amount_kopecks, "category_id": category["id"]}
        if comment is not None:
            payload["comment"] = comment
        return _json(_request(session, base_url, "POST", "/operations", payload))

    @tool
    def list_operations() -> str:
        """Список всех финансовых операций по возрастанию id."""
        return _json(_request(session, base_url, "GET", "/operations"))

    @tool
    def get_operation(operation_id: int) -> str:
        """Получить одну операцию по id."""
        return _json(_request(session, base_url, "GET", f"/operations/{operation_id}"))

    @tool
    def update_operation(
        operation_id: int,
        type: str | None = None,
        amount: str | None = None,
        category_name: str | None = None,
        comment: str | None = None,
    ) -> str:
        """Частично обновить операцию: меняются только переданные поля.
        amount — сумма строкой как сказал пользователь,
        конвертация в копейки выполняется автоматически.
        category_name: название категории (именительный падеж, единственное число) —
          инструмент сам найдёт категорию и вернёт ошибку, если её нет."""
        payload: dict = {}
        if type is not None:
            payload["type"] = type
        if amount is not None:
            try:
                payload["amount"] = to_kopecks(amount)
            except AmountParseError as exc:
                return _json({"ok": False, "error": str(exc)})
        if category_name is not None:
            resolved = _resolve_category(session, base_url, category_name)
            if not resolved["ok"]:
                return _json(resolved)
            category = resolved["data"]
            if type is not None and category["type"] != type:
                mismatch = (
                    f"category '{category['name']}' has type '{category['type']}', "
                    f"operation type is '{type}'"
                )
                return _json({"ok": False, "error": mismatch})
            payload["category_id"] = category["id"]
        if comment is not None:
            payload["comment"] = comment
        if not payload:
            return _json({"ok": False, "error": "no fields to update"})
        return _json(_request(session, base_url, "PATCH", f"/operations/{operation_id}", payload))

    @tool
    def get_balance() -> str:
        """Текущий баланс в копейках: {"balance": <income - expense>}."""
        return _json(_request(session, base_url, "GET", "/balance"))

    return [
        list_categories,
        create_operation,
        list_operations,
        get_operation,
        update_operation,
        get_balance,
    ]
