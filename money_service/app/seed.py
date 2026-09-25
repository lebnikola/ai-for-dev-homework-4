from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from .models import Category

DEFAULT_CATEGORIES: list[tuple[str, str]] = [
    ("Зарплата", "income"),
    ("Шабашки", "income"),
    ("Долги", "income"),
    ("Продукты", "expense"),
    ("Кино", "expense"),
    ("Театр", "expense"),
    ("Кофе", "expense"),
    ("Ресторан", "expense"),
    ("Столовая", "expense"),
    ("Бензин", "expense"),
    ("Квартплата", "expense"),
]


def seed_categories(session_factory: sessionmaker[Session]) -> None:
    with session_factory() as session:
        existing = set(session.scalars(select(Category.name)))
        new_categories = [
            Category(name=name, type=type_)
            for name, type_ in DEFAULT_CATEGORIES
            if name not in existing
        ]
        if new_categories:
            session.add_all(new_categories)
            session.commit()
