from flask import Blueprint, current_app, jsonify, request

from .models import Category, Operation
from .repositories import DuplicateCategoryError
from .validators import (
    ValidationError,
    validate_category,
    validate_operation,
    validate_operation_update,
)

bp = Blueprint("finance", __name__)


def _json_body() -> dict | None:
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return None
    return data


def _category_json(category: Category) -> dict:
    return {"id": category.id, "name": category.name, "type": category.type}


def _operation_json(operation: Operation) -> dict:
    return {
        "id": operation.id,
        "type": operation.type,
        "amount": operation.amount,
        "category_id": operation.category_id,
        "comment": operation.comment,
        "created_at": operation.created_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def _category_type_error(category_id: int, type_: str):
    category = current_app.extensions["category_repo"].get_by_id(category_id)
    if category is None:
        return jsonify({"error": f"Category {category_id} not found"}), 404
    if category.type != type_:
        return jsonify(
            {"error": f"Category type '{category.type}' does not match operation type '{type_}'"}
        ), 400
    return None


@bp.post("/categories")
def create_category():
    data = _json_body()
    if data is None:
        return jsonify({"error": "Request body must be valid JSON object"}), 400

    try:
        name, type_ = validate_category(data)
    except ValidationError as exc:
        return jsonify({"error": str(exc)}), 400

    repo = current_app.extensions["category_repo"]
    try:
        category = repo.create(name, type_)
    except DuplicateCategoryError:
        return jsonify({"error": f"Category '{name}' already exists"}), 409

    return jsonify(_category_json(category)), 201


@bp.get("/categories")
def list_categories():
    category_repo = current_app.extensions["category_repo"]
    categories = category_repo.list_all()
    return jsonify([_category_json(category) for category in categories]), 200


@bp.post("/operations")
def create_operation():
    data = _json_body()
    if data is None:
        return jsonify({"error": "Request body must be valid JSON object"}), 400

    try:
        type_, amount, category_id, comment = validate_operation(data)
    except ValidationError as exc:
        return jsonify({"error": str(exc)}), 400

    error = _category_type_error(category_id, type_)
    if error is not None:
        return error

    operation_repo = current_app.extensions["operation_repo"]
    operation = operation_repo.create(type_, amount, category_id, comment)

    return jsonify(_operation_json(operation)), 201


@bp.get("/operations")
def list_operations():
    operation_repo = current_app.extensions["operation_repo"]
    operations = operation_repo.list_all()
    return jsonify([_operation_json(operation) for operation in operations]), 200


@bp.get("/operations/<int:operation_id>")
def get_operation(operation_id: int):
    operation_repo = current_app.extensions["operation_repo"]
    operation = operation_repo.get_by_id(operation_id)
    if operation is None:
        return jsonify({"error": f"Operation {operation_id} not found"}), 404

    return jsonify(_operation_json(operation)), 200


@bp.patch("/operations/<int:operation_id>")
def update_operation(operation_id: int):
    data = _json_body()
    if data is None:
        return jsonify({"error": "Request body must be valid JSON object"}), 400

    try:
        fields = validate_operation_update(data)
    except ValidationError as exc:
        return jsonify({"error": str(exc)}), 400

    operation_repo = current_app.extensions["operation_repo"]
    operation = operation_repo.get_by_id(operation_id)
    if operation is None:
        return jsonify({"error": f"Operation {operation_id} not found"}), 404

    new_type = fields.get("type", operation.type)
    new_category_id = fields.get("category_id", operation.category_id)
    if new_type != operation.type or new_category_id != operation.category_id:
        error = _category_type_error(new_category_id, new_type)
        if error is not None:
            return error

    updated = operation_repo.update(operation_id, **fields)
    if updated is None:
        return jsonify({"error": f"Operation {operation_id} not found"}), 404

    return jsonify(_operation_json(updated)), 200


@bp.get("/balance")
def get_balance():
    operation_repo = current_app.extensions["operation_repo"]
    return jsonify({"balance": operation_repo.balance()}), 200
