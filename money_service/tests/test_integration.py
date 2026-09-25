from app import create_app
from app.repositories import DuplicateCategoryError


def test_real_repositories_persist_data():
    app = create_app()
    category_repo = app.extensions["category_repo"]
    operation_repo = app.extensions["operation_repo"]

    category = category_repo.create("Продукты", "expense")
    assert category.id == 1
    assert category_repo.get_by_id(1).name == "Продукты"
    assert category_repo.get_by_id(999) is None

    try:
        category_repo.create("Продукты", "expense")
    except DuplicateCategoryError:
        pass
    else:
        raise AssertionError("duplicate name must raise DuplicateCategoryError")

    operation = operation_repo.create("expense", 25000, 1, "Супермаркет")
    assert operation.id == 1
    assert operation.created_at is not None


def test_end_to_end_with_real_database():
    app = create_app()
    client = app.test_client()

    resp = client.post("/categories", json={"name": "Продукты", "type": "expense"})
    assert resp.status_code == 201
    category_id = resp.get_json()["id"]

    resp = client.post(
        "/operations",
        json={"type": "expense", "amount": 25000, "category_id": category_id},
    )
    assert resp.status_code == 201

    resp = client.post(
        "/operations",
        json={"type": "income", "amount": 100, "category_id": category_id},
    )
    assert resp.status_code == 400


def test_operations_crud_and_balance_with_real_database():
    app = create_app()
    client = app.test_client()

    expense_category_id = client.post(
        "/categories", json={"name": "Продукты", "type": "expense"}
    ).get_json()["id"]
    income_category_id = client.post(
        "/categories", json={"name": "Зарплата", "type": "income"}
    ).get_json()["id"]

    created = client.post(
        "/operations",
        json={"type": "expense", "amount": 25000, "category_id": expense_category_id},
    ).get_json()
    client.post(
        "/operations",
        json={"type": "income", "amount": 100000, "category_id": income_category_id},
    )

    resp = client.get(f"/operations/{created['id']}")
    assert resp.status_code == 200
    assert resp.get_json()["amount"] == 25000

    resp = client.patch(f"/operations/{created['id']}", json={"amount": 40000, "comment": "Оптом"})
    assert resp.status_code == 200
    assert resp.get_json()["amount"] == 40000
    assert resp.get_json()["comment"] == "Оптом"

    resp = client.get("/operations")
    assert resp.status_code == 200
    assert [item["id"] for item in resp.get_json()] == [1, 2]

    resp = client.get("/balance")
    assert resp.status_code == 200
    assert resp.get_json() == {"balance": 60000}


def test_balance_and_missing_operation_with_real_database():
    app = create_app()
    client = app.test_client()

    assert client.get("/balance").get_json() == {"balance": 0}
    assert client.get("/operations/1").status_code == 404
    assert client.patch("/operations/1", json={"amount": 100}).status_code == 404


def test_real_operation_repository_update_missing_returns_none():
    repo = create_app().extensions["operation_repo"]
    assert repo.update(999, amount=100) is None


def test_list_categories_with_real_database():
    app = create_app()
    client = app.test_client()

    assert client.get("/categories").get_json() == []

    expense_id = client.post(
        "/categories", json={"name": "Продукты", "type": "expense"}
    ).get_json()["id"]
    income_id = client.post("/categories", json={"name": "Зарплата", "type": "income"}).get_json()[
        "id"
    ]

    resp = client.get("/categories")
    assert resp.status_code == 200
    assert resp.get_json() == [
        {"id": expense_id, "name": "Продукты", "type": "expense"},
        {"id": income_id, "name": "Зарплата", "type": "income"},
    ]
