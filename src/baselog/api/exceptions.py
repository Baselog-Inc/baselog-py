"""
Custom exceptions for the baselog API client.

This module provides specific exception classes for different types of API errors
that can occur during HTTP communications with the baselog backend.
"""

from typing import Optional


class ConfigurationError(Exception):
    """Base exception for all configuration errors"""

    def __init__(self, message: str, context: Optional[str] = None):
        super().__init__(message)
        self.context = context

    def __str__(self) -> str:
        if self.context:
            return f"{self.args[0]} (context: {self.context})"
        return self.args[0]


class MissingConfigurationError(ConfigurationError):
    """Raised when required configuration is missing"""
    pass


class InvalidConfigurationError(ConfigurationError):
    """Raised when configuration values are invalid"""
    pass


class EnvironmentConfigurationError(ConfigurationError):
    """Raised when environment-specific configuration fails"""
    pass


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