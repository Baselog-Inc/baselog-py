from enum import Enum
from collections.abc import Sequence
from typing import Optional


class LoggerMode(Enum):
    """Represents the operational mode of the logger"""
    LOCAL = "local"
    API = "api"

    def __str__(self) -> str:
        return self.value

    def __repr__(self) -> str:
        return f"LoggerMode.{self.name}"


class Logger:
    def __init__(self, api_key=None, config=None):
        self._api_client = None
        self._config = None
        self._mode = LoggerMode.LOCAL  # Default to local mode

        if api_key or config:
            self._setup_api_client(api_key, config)
            self._mode = LoggerMode.API

    def _setup_api_client(self, api_key=None, config=None):
        """Setup API client and switch to API mode"""
        try:
            # Import here to avoid circular dependencies
            from .api.config import APIConfig
            from .api.client import APIClient

            if config:
                self._config = config
                self._api_client = APIClient(self._config)
            else:
                # Create default config with api_key
                self._config = APIConfig(api_key=api_key)
                self._api_client = APIClient(self._config)

            # Success: switch to API mode
            self._mode = LoggerMode.API
        except Exception:
            # Fallback to local mode on error
            self._mode = LoggerMode.LOCAL

    @property
    def mode(self) -> LoggerMode:
        """Get current operational mode"""
        return self._mode

    def is_api_mode(self) -> bool:
        """Check if logger is in API mode"""
        return self._mode == LoggerMode.API

    def is_local_mode(self) -> bool:
        """Check if logger is in local mode"""
        return self._mode == LoggerMode.LOCAL

    def info(
        self, message: str, *, category: Optional[str] = None, tags: Sequence[str] = []
    ) -> str:
        if self.is_api_mode() and self._api_client:
            # TODO: Implement actual API sending
            print(f"API mode: {message}", category, tags)
        else:
            print(message, category, tags)

    def debug(
        self, message: str, *, category: Optional[str] = None, tags: Sequence[str] = []
    ) -> str:
        if self.is_api_mode() and self._api_client:
            # TODO: Implement actual API sending
            print(f"API mode: {message}", category, tags)
        else:
            print(message, category, tags)

    def warning(
        self, message: str, *, category: Optional[str] = None, tags: Sequence[str] = []
    ) -> str:
        if self.is_api_mode() and self._api_client:
            # TODO: Implement actual API sending
            print(f"API mode: {message}", category, tags)
        else:
            print(message, category, tags)

    def error(
        self, message: str, *, category: Optional[str] = None, tags: Sequence[str] = []
    ) -> str:
        if self.is_api_mode() and self._api_client:
            # TODO: Implement actual API sending
            print(f"API mode: {message}", category, tags)
        else:
            print(message, category, tags)

    def critical(
        self, message: str, *, category: Optional[str] = None, tags: Sequence[str] = []
    ) -> str:
        if self.is_api_mode() and self._api_client:
            # TODO: Implement actual API sending
            print(f"API mode: {message}", category, tags)
        else:
            print(message, category, tags)
