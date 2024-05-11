class _Missing:
    """
    Represents a status of missing.
    """

    def __eq__(self, other) -> bool:
        return False

    def __bool__(self) -> bool:
        return False

    def __repr__(self) -> str:
        return "..."


MISSING = _Missing()
