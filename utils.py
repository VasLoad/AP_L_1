from typing import List, Dict, Any

from errors import EmptyValueError, InvalidTypeError, InvalidElementTypeError


def validate_str(value, field_name: str, allow_empty: bool = False):
    if not isinstance(value, str):
        raise InvalidTypeError(field_name, str, type(value).__name__)

    if not allow_empty and not value.strip():
        raise EmptyValueError(field_name)


def validate_list(value, field_name: str, expected_type: type):
    if not isinstance(value, list):
        raise InvalidTypeError(field_name, List[type], type(value).__name__)

    for element in value:
        if not isinstance(element, expected_type):
            raise InvalidElementTypeError(field_name, expected_type)


def deserialize_union(data: List[Any], types: List[type]) -> List[Any]:
    result = []

    type_names = {cls.__name__: cls for cls in types}

    for item in data:
        item_type_name = item.get("type")
        item_data = item.get("data")

        if item_type_name not in type_names:
            print(f"Неизвестный тип объекта: {item_type_name}.")

            continue

        item_type = type_names[item_type_name]

        if not hasattr(item_type, "deserialize"):
            print(f"У объекта {item_type_name} отсутствует атрибут \"deserialize\".")

            continue

        result.append(item_type.deserialize(item_data))

    return result
