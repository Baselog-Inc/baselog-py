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
        self._sync_client = None
        self._config = None
        self._mode = LoggerMode.LOCAL  # Default to local mode

        if api_key or config:
            self._setup_sync_client(api_key, config)
            self._mode = LoggerMode.API

    def _setup_sync_client(self, api_key=None, config=None):
        """Setup sync API client and switch to API mode"""
        try:
            # Import here to avoid circular dependencies
            from .api.config import APIConfig
            from .sync_client import SyncAPIClient

            if config:
                self._config = config
                self._sync_client = SyncAPIClient(self._config)
            else:
                # Create default config with api_key
                self._config = APIConfig(api_key=api_key)
                self._sync_client = SyncAPIClient(self._config)

            # Success: switch to API mode
            self._mode = LoggerMode.API
        except Exception as e:
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

    def _print_log_locally(self, level: str, message: str, category: Optional[str] = None, tags: Sequence[str] = []) -> None:
        """Helper method to print logs locally when API mode fails."""
        parts = [f"{level}: {message}"]
        if category:
            parts.append(f"Category: {category}")
        if tags:
            parts.append(f"Tags: {', '.join(tags)}")
        print(' '.join(parts))

    def info(
        self, message: str, *, category: Optional[str] = None, tags: Sequence[str] = []
    ) -> str:
        if self.is_api_mode() and self._sync_client:
            try:
                from .api.models import LogModel, LogLevel
                log_data = LogModel(
                    level=LogLevel.INFO,
                    message=message,
                    category=category,
                    tags=tags
                )
                self._sync_client.send_log_sync(log_data)
            except Exception:
                # Fallback to local logging on API error
                self._print_log_locally("INFO", message, category, tags)
        else:
            self._print_log_locally("INFO", message, category, tags)

    def debug(
        self, message: str, *, category: Optional[str] = None, tags: Sequence[str] = []
    ) -> str:
        if self.is_api_mode() and self._sync_client:
            try:
                from .api.models import LogModel, LogLevel
                log_data = LogModel(
                    level=LogLevel.DEBUG,
                    message=message,
                    category=category,
                    tags=tags
                )
                self._sync_client.send_log_sync(log_data)
            except Exception:
                # Fallback to local logging on API error
                self._print_log_locally("DEBUG", message, category, tags)
        else:
            self._print_log_locally("DEBUG", message, category, tags)

    def warning(
        self, message: str, *, category: Optional[str] = None, tags: Sequence[str] = []
    ) -> str:
        if self.is_api_mode() and self._sync_client:
            try:
                from .api.models import LogModel, LogLevel
                log_data = LogModel(
                    level=LogLevel.WARNING,
                    message=message,
                    category=category,
                    tags=tags
                )
                self._sync_client.send_log_sync(log_data)
            except Exception:
                # Fallback to local logging on API error
                self._print_log_locally("WARNING", message, category, tags)
        else:
            self._print_log_locally("WARNING", message, category, tags)

    def error(
        self, message: str, *, category: Optional[str] = None, tags: Sequence[str] = []
    ) -> str:
        if self.is_api_mode() and self._sync_client:
            try:
                from .api.models import LogModel, LogLevel
                log_data = LogModel(
                    level=LogLevel.ERROR,
                    message=message,
                    category=category,
                    tags=tags
                )
                self._sync_client.send_log_sync(log_data)
            except Exception:
                # Fallback to local logging on API error
                self._print_log_locally("ERROR", message, category, tags)
        else:
            self._print_log_locally("ERROR", message, category, tags)

    def critical(
        self, message: str, *, category: Optional[str] = None, tags: Sequence[str] = []
    ) -> str:
        if self.is_api_mode() and self._sync_client:
            try:
                from .api.models import LogModel, LogLevel
                log_data = LogModel(
                    level=LogLevel.CRITICAL,
                    message=message,
                    category=category,
                    tags=tags
                )
                self._sync_client.send_log_sync(log_data)
            except Exception:
                # Fallback to local logging on API error
                self._print_log_locally("CRITICAL", message, category, tags)
        else:
            self._print_log_locally("CRITICAL", message, category, tags)
