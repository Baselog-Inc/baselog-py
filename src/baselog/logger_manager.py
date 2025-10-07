import threading
from typing import Optional
from .logger import Logger
from .api.config import APIConfig, load_config
from .helpers import _auto_configure, _create_config_from_api_key
import logging


class LoggerManager:
    """
    Singleton manager for global logger instance and configuration.

    Provides thread-safe access to a single logger instance with
    lazy loading and auto-configuration capabilities.
    """

    _instance: Optional['LoggerManager'] = None
    _lock = threading.Lock()

    def __new__(cls) -> 'LoggerManager':
        """Singleton pattern implementation with thread safety."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize LoggerManager (called once due to singleton)."""
        if hasattr(self, '_initialized'):
            return  # Already initialized

        self._logger: Optional[Logger] = None
        self._configured: bool = False
        self._lock = threading.RLock()  # Reentrant lock for nested calls
        self.logger = logging.getLogger(__name__)
        self._initialized = True

    def get_logger(self) -> Logger:
        """
        Get current logger instance with lazy loading.

        Returns:
            Logger instance (auto-configured if not already configured)
        """
        if self._logger is None:
            with self._lock:
                if self._logger is None:
                    self._logger = self._auto_configure()
        return self._logger

    def configure(self, api_key: Optional[str] = None, config: Optional[APIConfig] = None, **kwargs) -> None:
        """
        Configure the global logger with new settings.

        Args:
            api_key: Direct API key for simple configuration
            config: Complete APIConfig object
            **kwargs: Additional configuration parameters
        """
        with self._lock:
            try:
                if config is not None:
                    self._logger = Logger(config=config)
                elif api_key is not None:
                    # Use helper function for config creation
                    api_config = _create_config_from_api_key(api_key, **kwargs)
                    self._logger = Logger(config=api_config)
                elif kwargs:
                    # Create config from kwargs using helper
                    api_key = kwargs.pop('api_key', None)
                    if api_key:
                        api_config = _create_config_from_api_key(api_key, **kwargs)
                        self._logger = Logger(config=api_config)
                    else:
                        # Reconfigure from environment
                        self._logger = _auto_configure()
                else:
                    # Reconfigure from environment
                    self._logger = _auto_configure()

                # Only set _configured to True if logger is in API mode
                if self._logger and self._logger.is_api_mode():
                    self._configured = True
                else:
                    self._configured = False

                self.logger.info("Logger configured successfully")

            except Exception as e:
                # Fallback to local logger using helper
                from .helpers import _create_local_logger
                self._logger = _create_local_logger()
                self._configured = False
                self.logger.warning(f"Configuration failed, using local logger: {e}")

    def is_configured(self) -> bool:
        """
        Check if logger is configured for API usage.

        Returns:
            True if logger is configured for API, False otherwise
        """
        if not self._configured or self._logger is None:
            return False
        return self._logger.is_api_mode

    def reset(self) -> None:
        """
        Reset logger to initial state (useful for testing).

        This method clears the current logger instance and configuration,
        forcing re-initialization on next access.
        """
        with self._lock:
            self._logger = None
            self._configured = False
            self.logger.debug("LoggerManager reset to initial state")

    def _auto_configure(self) -> Logger:
        """
        Auto-configure logger from environment variables.

        Returns:
            Configured Logger instance or local logger on failure
        """
        logger_instance = _auto_configure()
        self._configured = logger_instance.is_api_mode()
        return logger_instance

    def get_current_config(self) -> Optional[APIConfig]:
        """
        Get current configuration for debugging.

        Returns:
            Current APIConfig or None if in local mode
        """
        if self._logger and self._logger.config:
            return self._logger.config
        return None

    def get_status(self) -> dict:
        """
        Get current manager status for debugging.

        Returns:
            Dictionary with current status information
        """
        return {
            "configured": self._configured,
            "logger_mode": str(self._logger.mode) if self._logger else "None",
            "api_mode": self.is_configured(),
            "has_config": self.get_current_config() is not None
        }