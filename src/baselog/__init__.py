"""Baselog Python SDK - Simple and powerful logging for Python applications.

This module provides a clean, simple interface for logging with optional
API integration for remote log aggregation and monitoring.
"""

from typing import Optional, Sequence
from .logger import Logger
from .event import Event
from .api import config as config_module
from .logger_manager import LoggerManager
from .api.config import APIConfig
from .api.models import LogLevel

# Initialize the global logger manager
_manager = LoggerManager()

# Backward compatibility exports
logger = _manager.get_logger()
event = Event()
config = config_module

# Public API Functions
def configure(api_key: Optional[str] = None, config: Optional[APIConfig] = None, **kwargs) -> None:
    """
    Configure the global logger instance with API integration.

    This function allows you to configure the logger to send logs to the
    Baselog API backend. If not configured, the logger operates in local
    mode (print to console).

    Args:
        api_key: Direct API key for simple configuration
        config: Complete APIConfig object for advanced configuration
        **kwargs: Additional configuration parameters:
            - base_url: Override API base URL
            - environment: Override environment (development/staging/production)
            - timeouts: Override timeout configuration
            - retry_strategy: Override retry strategy

    Examples:
        # Simple configuration with API key
        baselog.configure(api_key="your-api-key")

        # Advanced configuration
        from baselog.api import APIConfig, Environment
        config = APIConfig(
            api_key="your-api-key",
            base_url="https://custom-api.com/v1",
            environment=Environment.PRODUCTION
        )
        baselog.configure(config=config)

        # Configuration with overrides
        baselog.configure(
            api_key="your-api-key",
            base_url="https://staging-api.com/v1",
            environment="staging"
        )
    """
    _manager.configure(api_key=api_key, config=config, **kwargs)

def info(message: str, *, category: Optional[str] = None, tags: Sequence[str] = []) -> None:
    """
    Log an INFO level message.

    Args:
        message: The log message
        category: Optional category for the log
        tags: Optional sequence of tags

    Examples:
        baselog.info("Application started")
        baselog.info("User logged in", category="auth", tags=["user", "login"])
    """
    logger = _manager.get_logger()
    logger.info(message, category=category, tags=tags)

def debug(message: str, *, category: Optional[str] = None, tags: Sequence[str] = []) -> None:
    """
    Log a DEBUG level message.

    Args:
        message: The log message
        category: Optional category for the log
        tags: Optional sequence of tags

    Examples:
        baselog.debug("Processing user data")
        baselog.debug("Cache hit", category="performance", tags=["cache"])
    """
    logger = _manager.get_logger()
    logger.debug(message, category=category, tags=tags)

def warning(message: str, *, category: Optional[str] = None, tags: Sequence[str] = []) -> None:
    """
    Log a WARNING level message.

    Args:
        message: The log message
        category: Optional category for the log
        tags: Optional sequence of tags

    Examples:
        baselog.warning("Deprecated API used")
        baselog.warning("High memory usage", category="performance", tags=["memory"])
    """
    logger = _manager.get_logger()
    logger.warning(message, category=category, tags=tags)

def error(message: str, *, category: Optional[str] = None, tags: Sequence[str] = []) -> None:
    """
    Log an ERROR level message.

    Args:
        message: The log message
        category: Optional category for the log
        tags: Optional sequence of tags

    Examples:
        baselog.error("Database connection failed")
        baselog.error("Payment processing failed", category="payment", tags=["critical"])
    """
    logger = _manager.get_logger()
    logger.error(message, category=category, tags=tags)

def critical(message: str, *, category: Optional[str] = None, tags: Sequence[str] = []) -> None:
    """
    Log a CRITICAL level message.

    Args:
        message: The log message
        category: Optional category for the log
        tags: Optional sequence of tags

    Examples:
        baselog.critical("System is down")
        baselog.critical("Security breach detected", category="security", tags=["breach"])
    """
    logger = _manager.get_logger()
    logger.critical(message, category=category, tags=tags)

def is_configured() -> bool:
    """
    Check if the global logger is configured for API usage.

    Returns:
        True if logger is configured for API, False if in local mode

    Examples:
        if baselog.is_configured():
            print("Logger is sending logs to API")
        else:
            print("Logger is using local mode")
    """
    return _manager.is_configured()

def reset() -> None:
    """
    Reset the global logger to initial state.

    This function is primarily useful for testing scenarios where you
    need to ensure a clean state. In normal operation, this should
    not be necessary.

    Examples:
        # In test setup
        baselog.reset()
        baselog.configure(api_key="test-key")
    """
    _manager.reset()

def get_status() -> dict:
    """
    Get current logger status for debugging.

    Returns:
        Dictionary with current status information

    Examples:
        status = baselog.get_status()
        print(f"Configured: {status['configured']}")
        print(f"Mode: {status['logger_mode']}")
    """
    return _manager.get_status()

def get_current_config() -> Optional[APIConfig]:
    """
    Get current configuration for debugging.

    Returns:
        Current APIConfig or None if in local mode

    Examples:
        config = baselog.get_current_config()
        if config:
            print(f"Base URL: {config.base_url}")
            print(f"Environment: {config.environment}")
    """
    return _manager.get_current_config()

# Module-level exports
__all__ = [
    # Core functions
    'configure', 'info', 'debug', 'warning', 'error', 'critical',

    # Utility functions
    'is_configured', 'reset', 'get_status', 'get_current_config',

    # Backward compatibility
    'logger', 'event', 'config',

    # Types and classes for advanced usage
    'APIConfig', 'LogLevel', 'Logger', 'Event'
]

# Version information
__version__ = "0.1.0"
__author__ = "Baselog Team"
__description__ = "Simple and powerful logging for Python applications"