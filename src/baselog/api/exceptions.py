"""
Custom exceptions for the baselog API client.

This module provides specific exception classes for different types of API errors
that can occur during HTTP communications with the baselog backend.
"""


class APIError(Exception):
    """Base exception for all API-related errors."""

    def __init__(self, message: str, status_code: int = None, retry_after: int = None, original_error: Exception = None):
        self.message = message
        self.status_code = status_code
        self.retry_after = retry_after
        self.original_error = original_error
        super().__init__(self.message)


class APIAuthenticationError(APIError):
    """Raised for authentication failures (401, 403)."""

    def __init__(self, message: str, status_code: int = None):
        super().__init__(message, status_code=status_code)


class APITimeoutError(APIError):
    """Raised for timeout-related errors."""

    def __init__(self, message: str, timeout_type: str = None):
        self.timeout_type = timeout_type
        super().__init__(message)


class APIRateLimitError(APIError):
    """Raised for rate limiting (429) with retry information."""

    def __init__(self, message: str, retry_after: int = None):
        super().__init__(message, retry_after=retry_after)


class APINetworkError(APIError):
    """Raised for network-related errors."""

    def __init__(self, message: str, original_error: Exception = None):
        super().__init__(message, original_error=original_error)