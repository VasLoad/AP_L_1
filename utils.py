from errors import EmptyValueError, InvalidTypeError, InvalidElementTypeError


def validate_str(value, field_name: str, allow_empty: bool = False):
    if not isinstance(value, str):
        raise InvalidTypeError(field_name, "str", type(value).__name__)

    if not allow_empty and not value.strip():
        raise EmptyValueError(field_name)


def validate_list(value, field_name: str, expected_type: type):
    if not isinstance(value, list):
        raise InvalidTypeError(field_name, f"List[{expected_type}]", type(value).__name__)

    for element in value:
        if not isinstance(element, expected_type):
            raise InvalidElementTypeError(field_name, expected_type.__name__)
