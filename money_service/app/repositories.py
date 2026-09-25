from sqlalchemy import case, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from .models import Category, Operation


class DuplicateCategoryError(Exception):
    pass


class CategoryRepository:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self.session_factory = session_factory

    def create(self, name: str, type_: str) -> Category:
        with self.session_factory() as session:
            category = Category(name=name, type=type_)
            session.add(category)
            try:
                session.commit()
            except IntegrityError as exc:
                session.rollback()
                raise DuplicateCategoryError(name) from exc
            return category

    def get_by_id(self, category_id: int) -> Category | None:
        with self.session_factory() as session:
            return session.get(Category, category_id)

    def list_all(self) -> list[Category]:
        with self.session_factory() as session:
            return list(session.scalars(select(Category).order_by(Category.id)))


class OperationRepository:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self.session_factory = session_factory

    def create(self, type_: str, amount: int, category_id: int, comment: str | None) -> Operation:
        with self.session_factory() as session:
            operation = Operation(
                type=type_, amount=amount, category_id=category_id, comment=comment
            )
            session.add(operation)
            session.commit()
            return operation

    def get_by_id(self, operation_id: int) -> Operation | None:
        with self.session_factory() as session:
            return session.get(Operation, operation_id)

    def list_all(self) -> list[Operation]:
        with self.session_factory() as session:
            return list(session.scalars(select(Operation).order_by(Operation.id)))

    def update(self, operation_id: int, **fields) -> Operation | None:
        with self.session_factory() as session:
            operation = session.get(Operation, operation_id)
            if operation is None:
                return None
            for field, value in fields.items():
                setattr(operation, field, value)
            session.commit()
            return operation

    def balance(self) -> int:
        signed_amount = case(
            (Operation.type == "income", Operation.amount),
            else_=-Operation.amount,
        )
        with self.session_factory() as session:
            total = session.execute(select(func.coalesce(func.sum(signed_amount), 0))).scalar_one()
        return int(total)
