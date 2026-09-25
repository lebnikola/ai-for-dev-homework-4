from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from app import create_app
from app.models import Category


def _post(client, payload):
    return client.post(
        "/operations",
        data=payload if isinstance(payload, (str, bytes)) else None,
        json=None if isinstance(payload, (str, bytes)) else payload,
        content_type="application/json",
    )


def _patch(client, operation_id, payload):
    return client.patch(
        f"/operations/{operation_id}",
        data=payload if isinstance(payload, (str, bytes)) else None,
        json=None if isinstance(payload, (str, bytes)) else payload,
        content_type="application/json",
    )


def _create_category(client, name, type_):
    resp = client.post("/categories", json={"name": name, "type": type_})
    assert resp.status_code == 201
    return resp.get_json()["id"]


def test_create_operation_success(client, operation_repo):
    client.post("/categories", json={"name": "Продукты", "type": "expense"})
    resp = _post(
        client,
        {"type": "expense", "amount": 25000, "category_id": 1, "comment": "Супермаркет"},
    )
    assert resp.status_code == 201
    assert resp.get_json() == {
        "id": 1,
        "type": "expense",
        "amount": 25000,
        "category_id": 1,
        "comment": "Супермаркет",
        "created_at": "2026-09-22T12:00:00Z",
    }
    assert operation_repo.created[-1].amount == 25000


def test_comment_is_optional(client):
    client.post("/categories", json={"name": "Зарплата", "type": "income"})
    resp = _post(client, {"type": "income", "amount": 100, "category_id": 1})
    assert resp.status_code == 201
    assert resp.get_json()["comment"] is None


def test_unreadable_json_returns_400(client):
    resp = _post(client, "{bad json")
    assert resp.status_code == 400
    assert "error" in resp.get_json()


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"type": "expense"},
        {"type": "expense", "amount": 100},
        {"type": "expense", "category_id": 1},
        {"type": "rent", "amount": 100, "category_id": 1},
        {"type": "expense", "amount": 0, "category_id": 1},
        {"type": "expense", "amount": -5, "category_id": 1},
        {"type": "expense", "amount": 10.5, "category_id": 1},
        {"type": "expense", "amount": "250", "category_id": 1},
        {"type": "expense", "amount": True, "category_id": 1},
        {"type": "expense", "amount": 100, "category_id": "abc"},
        {"type": "expense", "amount": 100, "category_id": 1.5},
        {"type": "expense", "amount": 100, "category_id": 1, "comment": "x" * 501},
        {"type": "expense", "amount": 100, "category_id": 1, "comment": 42},
    ],
)
def test_invalid_payload_returns_400(client, payload):
    resp = _post(client, payload)
    assert resp.status_code == 400
    assert "error" in resp.get_json()


def test_missing_category_returns_404(client):
    resp = _post(client, {"type": "expense", "amount": 100, "category_id": 99})
    assert resp.status_code == 404
    assert "error" in resp.get_json()


def test_type_mismatch_returns_400(client):
    client.post("/categories", json={"name": "Продукты", "type": "expense"})
    resp = _post(client, {"type": "income", "amount": 100, "category_id": 1})
    assert resp.status_code == 400
    assert "error" in resp.get_json()


def test_operation_created_with_server_timestamp():
    category_repo = MagicMock()
    category_repo.get_by_id.return_value = Category(id=1, name="Зарплата", type="income")

    operation_repo = MagicMock()
    from app.models import Operation

    created = Operation(
        id=7,
        type="income",
        amount=5000,
        category_id=1,
        comment=None,
        created_at=datetime(2026, 9, 22, 12, 0, 0, tzinfo=UTC),
    )
    operation_repo.create.return_value = created

    app = create_app(category_repo=category_repo, operation_repo=operation_repo, seed=False)
    resp = app.test_client().post(
        "/operations", json={"type": "income", "amount": 5000, "category_id": 1}
    )
    assert resp.status_code == 201
    assert operation_repo.create.call_args == (("income", 5000, 1, None),)
    assert resp.get_json()["created_at"] == "2026-09-22T12:00:00Z"


def test_get_operation_success(client):
    category_id = _create_category(client, "Продукты", "expense")
    created = client.post(
        "/operations", json={"type": "expense", "amount": 25000, "category_id": category_id}
    ).get_json()

    resp = client.get(f"/operations/{created['id']}")
    assert resp.status_code == 200
    assert resp.get_json() == created


def test_get_operation_not_found_returns_404(client):
    resp = client.get("/operations/99")
    assert resp.status_code == 404
    assert "error" in resp.get_json()


def test_list_operations_empty(client):
    resp = client.get("/operations")
    assert resp.status_code == 200
    assert resp.get_json() == []


def test_list_operations_returns_all_ordered_by_id(client, operation_repo):
    category_id = _create_category(client, "Продукты", "expense")
    client.post("/operations", json={"type": "expense", "amount": 100, "category_id": category_id})
    client.post("/operations", json={"type": "expense", "amount": 200, "category_id": category_id})

    resp = client.get("/operations")
    assert resp.status_code == 200
    body = resp.get_json()
    assert [item["id"] for item in body] == [1, 2]
    assert [item["amount"] for item in body] == [100, 200]


def test_patch_operation_success(client, operation_repo):
    category_id = _create_category(client, "Продукты", "expense")
    created = client.post(
        "/operations",
        json={"type": "expense", "amount": 25000, "category_id": category_id, "comment": "Рынок"},
    ).get_json()

    resp = _patch(client, created["id"], {"amount": 30000, "comment": "Супермаркет"})
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["amount"] == 30000
    assert body["comment"] == "Супермаркет"
    assert body["type"] == "expense"
    assert body["created_at"] == created["created_at"]
    assert operation_repo.created[0].amount == 30000


def test_patch_partial_update_keeps_other_fields(client):
    category_id = _create_category(client, "Продукты", "expense")
    created = client.post(
        "/operations",
        json={"type": "expense", "amount": 25000, "category_id": category_id, "comment": "Рынок"},
    ).get_json()

    resp = _patch(client, created["id"], {"comment": "Магазин у дома"})
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["amount"] == 25000
    assert body["category_id"] == category_id
    assert body["comment"] == "Магазин у дома"


def test_patch_can_clear_comment(client):
    category_id = _create_category(client, "Продукты", "expense")
    created = client.post(
        "/operations",
        json={"type": "expense", "amount": 100, "category_id": category_id, "comment": "Рынок"},
    ).get_json()

    resp = _patch(client, created["id"], {"comment": None})
    assert resp.status_code == 200
    assert resp.get_json()["comment"] is None


def test_patch_can_change_category(client):
    old_category_id = _create_category(client, "Продукты", "expense")
    new_category_id = _create_category(client, "Кафе", "expense")
    created = client.post(
        "/operations", json={"type": "expense", "amount": 100, "category_id": old_category_id}
    ).get_json()

    resp = _patch(client, created["id"], {"category_id": new_category_id})
    assert resp.status_code == 200
    assert resp.get_json()["category_id"] == new_category_id


def test_patch_calls_repository_update_with_validated_fields():
    operation_repo = MagicMock()
    from app.models import Operation

    stored = Operation(
        id=3,
        type="expense",
        amount=100,
        category_id=1,
        comment=None,
        created_at=datetime(2026, 9, 22, 12, 0, 0, tzinfo=UTC),
    )
    operation_repo.get_by_id.return_value = stored
    operation_repo.update.return_value = stored

    app = create_app(category_repo=MagicMock(), operation_repo=operation_repo, seed=False)
    resp = app.test_client().patch("/operations/3", json={"amount": 500})

    assert resp.status_code == 200
    operation_repo.update.assert_called_once_with(3, amount=500)


@pytest.mark.parametrize(
    "payload",
    [
        {},
        "{bad json",
        {"amount": 0},
        {"amount": -5},
        {"amount": 10.5},
        {"amount": "250"},
        {"type": "rent"},
        {"category_id": "abc"},
        {"comment": 42},
        {"comment": "x" * 501},
        {"id": 5},
        {"created_at": "2026-01-01T00:00:00Z"},
    ],
)
def test_patch_invalid_payload_returns_400(client, payload):
    category_id = _create_category(client, "Продукты", "expense")
    created = client.post(
        "/operations", json={"type": "expense", "amount": 100, "category_id": category_id}
    ).get_json()

    resp = _patch(client, created["id"], payload)
    assert resp.status_code == 400
    assert "error" in resp.get_json()


def test_patch_missing_operation_returns_404(client):
    resp = _patch(client, 99, {"amount": 100})
    assert resp.status_code == 404
    assert "error" in resp.get_json()


def test_patch_operation_lost_during_update_returns_404():
    operation_repo = MagicMock()
    from app.models import Operation

    stored = Operation(
        id=3,
        type="expense",
        amount=100,
        category_id=1,
        comment=None,
        created_at=datetime(2026, 9, 22, 12, 0, 0, tzinfo=UTC),
    )
    operation_repo.get_by_id.return_value = stored
    operation_repo.update.return_value = None

    app = create_app(category_repo=MagicMock(), operation_repo=operation_repo, seed=False)
    resp = app.test_client().patch("/operations/3", json={"amount": 500})

    assert resp.status_code == 404
    assert "error" in resp.get_json()


def test_patch_unknown_category_returns_404(client):
    category_id = _create_category(client, "Продукты", "expense")
    created = client.post(
        "/operations", json={"type": "expense", "amount": 100, "category_id": category_id}
    ).get_json()

    resp = _patch(client, created["id"], {"category_id": 99})
    assert resp.status_code == 404
    assert "error" in resp.get_json()


def test_patch_type_mismatch_returns_400(client):
    category_id = _create_category(client, "Продукты", "expense")
    created = client.post(
        "/operations", json={"type": "expense", "amount": 100, "category_id": category_id}
    ).get_json()

    resp = _patch(client, created["id"], {"type": "income"})
    assert resp.status_code == 400
    assert "error" in resp.get_json()


def test_patch_category_type_mismatch_returns_400(client):
    expense_category_id = _create_category(client, "Продукты", "expense")
    income_category_id = _create_category(client, "Зарплата", "income")
    created = client.post(
        "/operations", json={"type": "expense", "amount": 100, "category_id": expense_category_id}
    ).get_json()

    resp = _patch(client, created["id"], {"category_id": income_category_id})
    assert resp.status_code == 400
    assert "error" in resp.get_json()


def test_balance_without_operations_is_zero(client):
    resp = client.get("/balance")
    assert resp.status_code == 200
    assert resp.get_json() == {"balance": 0}


def _add_operation(client, name, type_, amount):
    category_id = _create_category(client, name, type_)
    resp = client.post(
        "/operations", json={"type": type_, "amount": amount, "category_id": category_id}
    )
    assert resp.status_code == 201


@pytest.mark.parametrize(
    ("operations", "expected"),
    [
        ([("Зарплата", "income", 100000)], 100000),
        ([("Продукты", "expense", 25000)], -25000),
        ([("Зарплата", "income", 100000), ("Продукты", "expense", 40000)], 60000),
        ([("Продукты", "expense", 40000), ("Развлечение", "expense", 30000)], -70000),
    ],
)
def test_balance_sums_income_minus_expense(client, operations, expected):
    for name, type_, amount in operations:
        _add_operation(client, name, type_, amount)

    resp = client.get("/balance")
    assert resp.status_code == 200
    assert resp.get_json() == {"balance": expected}
