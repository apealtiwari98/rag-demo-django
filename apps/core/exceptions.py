from typing import Any


class ApplicationError(Exception):
    """
    Raised by services for business-rule violations. The exception handler
    turns it into a 400 with {"message": ..., "extra": {...}}.
    """

    def __init__(self, message: str, extra: dict[str, Any] | None = None):
        super().__init__(message)
        self.message = message
        self.extra = extra or {}
