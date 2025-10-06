from enum import Enum
from collections.abc import Sequence
from typing import Optional
import logging


class LoggerMode(Enum):
    """Represents the operational mode of the logger"""
    LOCAL = "local"
    API = "api"

    def __str__(self) -> str:
        return self.value

    def __repr__(self) -> str:
        return f"LoggerMode.{self.name}"


class Logger:
    """
    Enhanced logger that can operate in both API and local modes.

    Supports both remote API logging and local print logging with
    automatic fallback to local logging on API failures.
    """

    def __init__(self, api_key: Optional[str] = None, config: Optional['APIConfig'] = None):
        """
        Initialize Logger with optional API configuration.

        Args:
            api_key: Direct API key for simple configuration
            config: Complete APIConfig object for advanced configuration

        Note:
            If neither api_key nor config is provided, logger operates in local mode only.
            If both are provided, config takes precedence over api_key.
        """
        self.logger = logging.getLogger(__name__)
        self._sync_client: Optional['SyncAPIClient'] = None
        self._config: Optional['APIConfig'] = None
        self._mode: LoggerMode = LoggerMode.LOCAL  # Default to local mode

        # Setup API client if configuration provided
        if api_key or config:
            self._setup_api_client(api_key, config)

    def _setup_api_client(self, api_key: Optional[str] = None, config: Optional['APIConfig'] = None):
        """
        Setup API client with proper configuration and error handling.

        Args:
            api_key: Direct API key (used if config is None)
            config: Complete APIConfig object for advanced configuration
        """
        try:
            # Resolve final configuration
            final_config = self._resolve_config(api_key, config)

            # Create SyncAPIClient
            from .sync_client import SyncAPIClient
            self._sync_client = SyncAPIClient(final_config)
            self._config = final_config
            self._mode = LoggerMode.API

            self.logger.debug(f"Logger configured for API mode with base_url: {final_config.base_url}")

        except Exception as e:
            # Fallback to local mode on any error
            self._mode = LoggerMode.LOCAL
            self._sync_client = None
            self._config = None

            self.logger.warning(f"Failed to setup API client, falling back to local logging: {e}")

    def _resolve_config(self, api_key: Optional[str] = None, config: Optional['APIConfig'] = None) -> 'APIConfig':
        """
        Resolve the final configuration from provided parameters.

        Args:
            api_key: Direct API key
            config: Complete APIConfig object

        Returns:
            APIConfig object ready for use

        Raises:
            ValueError: If no valid configuration can be created
        """
        if config is not None:
            # Use provided config (validate it has required fields)
            self._validate_config(config)
            return config

        elif api_key is not None:
            # Create config from API key with defaults
            return self._create_config_from_api_key(api_key)

        else:
            raise ValueError("Either api_key or config must be provided")

    def _validate_config(self, config: 'APIConfig') -> None:
        """Validate configuration parameters."""
        if not config.api_key or not isinstance(config.api_key, str):
            raise ValueError("API key must be a non-empty string")

        if not config.base_url or not isinstance(config.base_url, str):
            raise ValueError("Base URL must be a non-empty string")

        if config.timeouts.connect <= 0:
            raise ValueError("Connect timeout must be positive")

        if config.retry_strategy.max_attempts <= 0:
            raise ValueError("Max attempts must be positive")

    def _create_config_from_api_key(self, api_key: str) -> 'APIConfig':
        """
        Create APIConfig from API key with sensible defaults.

        Args:
            api_key: API key string

        Returns:
            APIConfig object with defaults
        """
        from .api.config import APIConfig, Timeouts, RetryStrategy, Environment

        return APIConfig(
            api_key=api_key,
            base_url="https://api.baselog.io/v1",  # Default base URL
            environment=Environment.DEVELOPMENT,   # Default environment
            timeouts=Timeouts.from_env(),          # Load from environment or defaults
            retry_strategy=RetryStrategy.from_env() # Load from environment or defaults
        )

    # Properties for accessing logger state
    @property
    def mode(self) -> LoggerMode:
        """Get current operational mode"""
        return self._mode

    @property
    def config(self) -> Optional['APIConfig']:
        """Get current configuration (None for local mode)."""
        return self._config

    def is_api_mode(self) -> bool:
        """Check if logger is in API mode"""
        return self._mode == LoggerMode.API

    def is_local_mode(self) -> bool:
        """Check if logger is in local mode"""
        return self._mode == LoggerMode.LOCAL

    def get_api_info(self) -> Optional[dict]:
        """
        Get API configuration info for debugging.

        Returns:
            Dictionary with API info or None if in local mode
        """
        if not self.is_api_mode() or not self._config:
            return None

        # Mask API key for security
        api_key_masked = self._config.api_key[:4] + "..." + self._config.api_key[-4:] if len(self._config.api_key) > 8 else "***"

        return {
            "base_url": self._config.base_url,
            "environment": self._config.environment.value if hasattr(self._config.environment, 'value') else str(self._config.environment),
            "api_key_masked": api_key_masked,
            "timeouts": {
                "connect": self._config.timeouts.connect,
                "read": self._config.timeouts.read,
                "write": self._config.timeouts.write,
                "pool": self._config.timeouts.pool
            },
            "retry_strategy": {
                "max_attempts": self._config.retry_strategy.max_attempts,
                "backoff_factor": self._config.retry_strategy.backoff_factor
            }
        }

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
