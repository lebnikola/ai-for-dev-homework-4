VALID_TYPES = ("income", "expense")
NAME_MIN_LENGTH = 1
NAME_MAX_LENGTH = 100
COMMENT_MAX_LENGTH = 500
OPERATION_FIELDS = ("type", "amount", "category_id", "comment")
IMMUTABLE_OPERATION_FIELDS = ("id", "created_at")


class ValidationError(ValueError):
    pass


def _require_int(value, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError(f"Field '{field}' must be an integer")
    return value


def _check_type(value) -> str:
    if value not in VALID_TYPES:
        raise ValidationError("Field 'type' must be one of: income, expense")
    return value


def _check_amount(value) -> int:
    amount = _require_int(value, "amount")
    if amount <= 0:
        raise ValidationError("Field 'amount' must be greater than 0")
    return amount


def _check_category_id(value) -> int:
    return _require_int(value, "category_id")


def _check_comment(value) -> str | None:
    if value is not None:
        if not isinstance(value, str):
            raise ValidationError("Field 'comment' must be a string")
        if len(value) > COMMENT_MAX_LENGTH:
            raise ValidationError(
                f"Field 'comment' must be at most {COMMENT_MAX_LENGTH} characters"
            )
    return value


def validate_category(data: dict) -> tuple[str, str]:
    if "name" not in data:
        raise ValidationError("Field 'name' is required")
    if "type" not in data:
        raise ValidationError("Field 'type' is required")

    name = data["name"]
    if not isinstance(name, str):
        raise ValidationError("Field 'name' must be a string")
    name = name.strip()
    if not NAME_MIN_LENGTH <= len(name) <= NAME_MAX_LENGTH:
        raise ValidationError(
            f"Field 'name' must be between {NAME_MIN_LENGTH} and {NAME_MAX_LENGTH} characters"
        )

    type_ = _check_type(data["type"])

    return name, type_


def validate_operation(data: dict) -> tuple[str, int, int, str | None]:
    for field in ("type", "amount", "category_id"):
        if field not in data:
            raise ValidationError(f"Field '{field}' is required")

    type_ = _check_type(data["type"])
    amount = _check_amount(data["amount"])
    category_id = _check_category_id(data["category_id"])
    comment = _check_comment(data.get("comment"))

    return type_, amount, category_id, comment


def validate_operation_update(data: dict) -> dict:
    for field in IMMUTABLE_OPERATION_FIELDS:
        if field in data:
            raise ValidationError(f"Field '{field}' cannot be updated")

    provided = [field for field in OPERATION_FIELDS if field in data]
    if not provided:
        raise ValidationError(
            f"Request body must contain at least one of: {', '.join(OPERATION_FIELDS)}"
        )

    fields: dict = {}
    if "type" in data:
        fields["type"] = _check_type(data["type"])
    if "amount" in data:
        fields["amount"] = _check_amount(data["amount"])
    if "category_id" in data:
        fields["category_id"] = _check_category_id(data["category_id"])
    if "comment" in data:
        fields["comment"] = _check_comment(data["comment"])

    return fields
