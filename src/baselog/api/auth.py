"""Authentication module for API key management."""

from dataclasses import dataclass
from typing import Dict
import re


class AuthenticationError(Exception):
    """Raised for authentication-related errors."""
    pass


class InvalidAPIKeyError(AuthenticationError):
    """Raised for invalid API key format."""
    pass


class MissingAPIKeyError(AuthenticationError):
    """Raised when API key is missing."""
    pass


@dataclass
class AuthManager:
    """Centralized API key authentication manager."""

    api_key: str

    def __post_init__(self) -> None:
        """Validate and sanitize API key after initialization."""
        self.api_key = self.validate_api_key(self.api_key)
        self._masked_key = self._mask_api_key(self.api_key)

    @classmethod
    def from_config(cls, api_key: str) -> 'AuthManager':
        """Factory method to create AuthManager from configuration.

        Args:
            api_key: The API key to use for authentication

        Returns:
            AuthManager instance

        Raises:
            InvalidAPIKeyError: If the API key is invalid
        """
        return cls(api_key=api_key)

    def validate_api_key(self, api_key: str) -> str:
        """Validate API key format and sanitize.

        Args:
            api_key: The API key to validate

        Returns:
            Sanitized API key

        Raises:
            ValueError: If API key is not a non-empty string
            InvalidAPIKeyError: If API key format is invalid
        """
        if not api_key or not isinstance(api_key, str):
            raise ValueError("API key must be a non-empty string")

        # Remove whitespace and validate format
        sanitized_key = api_key.strip()
        if len(sanitized_key) < 16:
            raise InvalidAPIKeyError("API key must be at least 16 characters long")

        # Basic format validation (alphanumeric with allowed special chars)
        if not re.match(r'^[a-zA-Z0-9\-_\.+=]+$', sanitized_key):
            raise InvalidAPIKeyError("API key contains invalid characters")

        return sanitized_key

    def get_auth_headers(self) -> Dict[str, str]:
        """Generate authentication headers for API requests.

        Returns:
            Dictionary containing authentication headers
        """
        return {
            'X-API-Key': self.api_key,
            'Content-Type': 'application/json',
            'User-Agent': 'baselog-python-client/1.0'
        }

    def get_masked_api_key(self) -> str:
        """Return a masked version of API key for safe logging/display.

        Returns:
            Masked API key (e.g., 'abcd...1234')
        """
        return self._masked_key

    def _mask_api_key(self, api_key: str) -> str:
        """Create a masked version of API key.

        Args:
            api_key: The API key to mask

        Returns:
            Masked version of the API key
        """
        if len(api_key) < 8:
            return "*" * len(api_key)
        return f"{api_key[:4]}...{api_key[-4:]}"