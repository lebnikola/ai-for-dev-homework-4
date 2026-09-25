from datetime import UTC, datetime

import pytest

from app import create_app
from app.models import Category


class FakeCategoryRepository:
    def __init__(self, existing=None):
        self.created = []
        self.existing = {name for name in (existing or [])}
        self._next_id = 1

    def create(self, name, type_):
        from app.repositories import DuplicateCategoryError

        if name in self.existing:
            raise DuplicateCategoryError(name)
        category = Category(id=self._next_id, name=name, type=type_)
        self._next_id += 1
        self.created.append(category)
        self.existing.add(name)
        return category

    def get_by_id(self, category_id):
        for category in self.created:
            if category.id == category_id:
                return category
        return None

    def list_all(self):
        return list(self.created)


class FakeOperationRepository:
    def __init__(self):
        self.created = []
        self._next_id = 1

    def create(self, type_, amount, category_id, comment):
        from app.models import Operation

        operation = Operation(
            id=self._next_id,
            type=type_,
            amount=amount,
            category_id=category_id,
            comment=comment,
            created_at=datetime(2026, 9, 22, 12, 0, 0, tzinfo=UTC),
        )
        self._next_id += 1
        self.created.append(operation)
        return operation

    def get_by_id(self, operation_id):
        for operation in self.created:
            if operation.id == operation_id:
                return operation
        return None

    def list_all(self):
        return list(self.created)

    def update(self, operation_id, **fields):
        operation = self.get_by_id(operation_id)
        if operation is None:
            return None
        for field, value in fields.items():
            setattr(operation, field, value)
        return operation

    def balance(self):
        total = 0
        for operation in self.created:
            total += operation.amount if operation.type == "income" else -operation.amount
        return total


@pytest.fixture
def category_repo():
    return FakeCategoryRepository()


@pytest.fixture
def operation_repo():
    return FakeOperationRepository()


@pytest.fixture
def client(category_repo, operation_repo):
    app = create_app(category_repo=category_repo, operation_repo=operation_repo, seed=False)
    return app.test_client()
