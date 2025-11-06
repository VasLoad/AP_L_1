class DataError(Exception):
    """Базовые исключения, связанные с данными"""

    pass


class EmptyValueError(DataError):
    """Ошибка пустого поля"""

    def __init__(self, field_name: str):
        super().__init__(f"Поле \"{field_name}\" не может быть пустым.")


class InvalidTypeError(DataError):
    """Ошибка неверного типа данных"""

    def __init__(self, field_name: str, expected_type: str, actual_type: str):
        super().__init__(f"Неверный тип данных для поля \"{field_name}\": ожидался {expected_type}, получен {actual_type}.")


class InvalidElementTypeError(DataError):
    """Ошибка неверного типа данных объекта списка"""

    def __init__(self, field_name: str, expected_type: str):
        super().__init__(f"Список \"{field_name}\" должен содержать только объекты типа {expected_type}.")


class CustomIndexError(DataError):
    """Кастомная ошибка индекса"""

    def __init__(self):
        super().__init__("Ошибка! Такого индекса не существует!")
