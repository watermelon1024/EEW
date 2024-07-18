from typing import Any


class Missing:
    """
    Represents a status of missing.
    """

    def __eq__(self, other) -> bool:
        return False

    def __bool__(self) -> bool:
        return False

    def __repr__(self) -> str:
        return "..."

    def __int__(self) -> int:
        return 0

    def __iter__(self):
        return iter([])


MISSING: Any = Missing()
