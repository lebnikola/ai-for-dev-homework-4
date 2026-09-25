from flask import Flask

from .database import build_engine, build_session_factory
from .models import Base
from .repositories import CategoryRepository, OperationRepository
from .routes import bp
from .seed import seed_categories


def create_app(category_repo=None, operation_repo=None, seed: bool = True) -> Flask:
    engine = build_engine()
    Base.metadata.create_all(engine)
    session_factory = build_session_factory(engine)
    if seed:
        seed_categories(session_factory)

    app = Flask(__name__)
    app.extensions["category_repo"] = category_repo or CategoryRepository(session_factory)
    app.extensions["operation_repo"] = operation_repo or OperationRepository(session_factory)
    app.register_blueprint(bp)
    return app
