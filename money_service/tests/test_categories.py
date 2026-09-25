from unittest.mock import MagicMock

import pytest

from app.repositories import DuplicateCategoryError


def _post(client, payload):
    return client.post(
        "/categories",
        data=payload if isinstance(payload, (str, bytes)) else None,
        json=None if isinstance(payload, (str, bytes)) else payload,
        content_type="application/json",
    )


def test_create_category_success(client, category_repo):
    resp = _post(client, {"name": "Продукты", "type": "expense"})
    assert resp.status_code == 201
    assert resp.get_json() == {"id": 1, "name": "Продукты", "type": "expense"}
    assert category_repo.created[-1].name == "Продукты"


def test_name_is_trimmed_before_save(client, category_repo):
    resp = _post(client, {"name": "  Продукты  ", "type": "income"})
    assert resp.status_code == 201
    assert category_repo.created[-1].name == "Продукты"
    assert resp.get_json()["name"] == "Продукты"


def test_unreadable_json_returns_400(client):
    resp = _post(client, "{not json")
    assert resp.status_code == 400
    assert "error" in resp.get_json()


def test_empty_body_returns_400(client):
    resp = client.post("/categories", data="", content_type="application/json")
    assert resp.status_code == 400
    assert "error" in resp.get_json()


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"name": "Продукты"},
        {"type": "expense"},
        {"name": "", "type": "expense"},
        {"name": "   ", "type": "expense"},
        {"name": 123, "type": "expense"},
        {"name": "a" * 101, "type": "expense"},
        {"name": "Продукты", "type": "rent"},
        {"name": "Продукты", "type": None},
    ],
)
def test_invalid_payload_returns_400(client, payload):
    resp = _post(client, payload)
    assert resp.status_code == 400
    assert "error" in resp.get_json()


def test_duplicate_name_returns_409(client, category_repo):
    category_repo.existing.add("Продукты")
    resp = _post(client, {"name": "Продукты", "type": "expense"})
    assert resp.status_code == 409
    assert "error" in resp.get_json()


def test_list_categories_empty(client):
    resp = client.get("/categories")
    assert resp.status_code == 200
    assert resp.get_json() == []


def test_list_categories_returns_created(client, category_repo):
    _post(client, {"name": "Продукты", "type": "expense"})
    _post(client, {"name": "Зарплата", "type": "income"})
    resp = client.get("/categories")
    assert resp.status_code == 200
    assert resp.get_json() == [
        {"id": 1, "name": "Продукты", "type": "expense"},
        {"id": 2, "name": "Зарплата", "type": "income"},
    ]


def test_duplicate_error_from_mocked_repo_returns_409():
    mocked_repo = MagicMock()
    mocked_repo.create.side_effect = DuplicateCategoryError("Продукты")
    app = create_app_stub(mocked_repo)
    resp = app.test_client().post("/categories", json={"name": "Продукты", "type": "expense"})
    assert resp.status_code == 409
    assert resp.get_json()["error"] == "Category 'Продукты' already exists"


def create_app_stub(category_repo):
    from app import create_app

    return create_app(category_repo=category_repo, operation_repo=MagicMock())
