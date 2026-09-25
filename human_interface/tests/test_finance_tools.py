import json

import pytest
import requests
import responses

from finance_tools import build_tools

BASE_URL = "http://test-api"


@pytest.fixture
def tools():
    return {t.name: t for t in build_tools(BASE_URL)}


@responses.activate
def test_create_operation_success(tools):
    responses.get(
        f"{BASE_URL}/categories",
        json=[{"id": 1, "name": "Продукты", "type": "expense"}],
        status=200,
    )
    responses.post(
        f"{BASE_URL}/operations",
        json={
            "id": 1,
            "type": "expense",
            "amount": 500_000,
            "category_id": 1,
            "comment": "Супермаркет",
            "created_at": "2026-09-24T10:00:00Z",
        },
        status=201,
    )
    result = json.loads(
        tools["create_operation"].invoke(
            {
                "type": "expense",
                "amount": "5 000",
                "category_name": "Продукты",
                "comment": "Супермаркет",
            }
        )
    )
    assert result == {
        "ok": True,
        "data": {
            "id": 1,
            "type": "expense",
            "amount": 500_000,
            "category_id": 1,
            "comment": "Супермаркет",
            "created_at": "2026-09-24T10:00:00Z",
        },
    }
    assert json.loads(responses.calls[1].request.body) == {
        "type": "expense",
        "amount": 500_000,
        "category_id": 1,
        "comment": "Супермаркет",
    }


@responses.activate
def test_create_operation_inflected_name_resolves(tools):
    responses.get(
        f"{BASE_URL}/categories",
        json=[{"id": 4, "name": "Мебель", "type": "expense"}],
        status=200,
    )
    responses.post(
        f"{BASE_URL}/operations",
        json={
            "id": 1,
            "type": "expense",
            "amount": 34_532,
            "category_id": 4,
            "comment": None,
            "created_at": "2026-09-24T10:00:00Z",
        },
        status=201,
    )
    result = json.loads(
        tools["create_operation"].invoke(
            {"type": "expense", "amount": "345.32", "category_name": "мебели"}
        )
    )
    assert result["ok"] is True
    assert json.loads(responses.calls[1].request.body)["category_id"] == 4


@responses.activate
def test_create_operation_unknown_category_no_http_post(tools):
    responses.get(
        f"{BASE_URL}/categories",
        json=[{"id": 1, "name": "Продукты", "type": "expense"}],
        status=200,
    )
    result = json.loads(
        tools["create_operation"].invoke(
            {"type": "expense", "amount": "5000", "category_name": "Мебель"}
        )
    )
    assert result["ok"] is False
    assert "unknown category" in result["error"]
    assert len(responses.calls) == 1


@responses.activate
def test_create_operation_type_mismatch_no_http_post(tools):
    responses.get(
        f"{BASE_URL}/categories",
        json=[{"id": 2, "name": "Зарплата", "type": "income"}],
        status=200,
    )
    result = json.loads(
        tools["create_operation"].invoke(
            {"type": "expense", "amount": "5000", "category_name": "Зарплата"}
        )
    )
    assert result["ok"] is False
    assert "has type 'income'" in result["error"]
    assert len(responses.calls) == 1


def test_create_operation_bad_amount_no_http(tools):
    result = json.loads(
        tools["create_operation"].invoke(
            {"type": "expense", "amount": "abc", "category_name": "Продукты"}
        )
    )
    assert result["ok"] is False
    assert "cannot parse amount" in result["error"]


@responses.activate
def test_connection_error(tools):
    responses.get(f"{BASE_URL}/balance", body=requests.ConnectionError("connection refused"))
    result = json.loads(tools["get_balance"].invoke({}))
    assert result["ok"] is False
    assert "ConnectionError" in result["error"]


@responses.activate
def test_list_categories_success(tools):
    responses.get(
        f"{BASE_URL}/categories",
        json=[{"id": 1, "name": "Продукты", "type": "expense"}],
        status=200,
    )
    result = json.loads(tools["list_categories"].invoke({}))
    assert result["ok"] is True
    assert result["data"][0]["name"] == "Продукты"


@responses.activate
def test_update_operation_success_converts_amount(tools):
    responses.patch(
        f"{BASE_URL}/operations/1",
        json={
            "id": 1,
            "type": "expense",
            "amount": 300_000,
            "category_id": 1,
            "comment": None,
            "created_at": "2026-09-24T10:00:00Z",
        },
        status=200,
    )
    result = json.loads(tools["update_operation"].invoke({"operation_id": 1, "amount": "3000"}))
    assert result["ok"] is True
    assert json.loads(responses.calls[0].request.body) == {"amount": 300_000}


@responses.activate
def test_update_operation_category_name_resolves(tools):
    responses.get(
        f"{BASE_URL}/categories",
        json=[{"id": 4, "name": "Кино", "type": "expense"}],
        status=200,
    )
    responses.patch(
        f"{BASE_URL}/operations/1",
        json={
            "id": 1,
            "type": "expense",
            "amount": 500_000,
            "category_id": 4,
            "comment": None,
            "created_at": "2026-09-24T10:00:00Z",
        },
        status=200,
    )
    result = json.loads(
        tools["update_operation"].invoke({"operation_id": 1, "category_name": "Кино"})
    )
    assert result["ok"] is True
    assert json.loads(responses.calls[1].request.body) == {"category_id": 4}


def test_update_operation_no_fields(tools):
    result = json.loads(tools["update_operation"].invoke({"operation_id": 1}))
    assert result == {"ok": False, "error": "no fields to update"}


@responses.activate
def test_non_json_error_body(tools):
    responses.get(
        f"{BASE_URL}/operations", body="<html>500</html>", status=500, content_type="text/html"
    )
    result = json.loads(tools["list_operations"].invoke({}))
    assert result == {"ok": False, "error": "HTTP 500"}
