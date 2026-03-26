"""Custom exceptions for ue_bridge."""
from __future__ import annotations


class UECommandError(Exception):
    """Raised when a command to Unreal Editor fails."""

    def __init__(self, message: str, error_type: str = "unknown",
                 recoverable: bool = True, data: dict | None = None):
        self.error_type = error_type
        self.recoverable = recoverable
        self.data = data or {}
        super().__init__(message)


class UEConnectionError(Exception):
    """Raised when connection to Unreal Editor fails."""
    pass
