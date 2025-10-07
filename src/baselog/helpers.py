"""Internal helper functions for logger configuration and management."""

import os
import logging
from typing import Optional
from .logger import Logger
from .api.config import APIConfig, load_config, Timeouts, RetryStrategy, Environment
from .api.exceptions import ConfigurationError

logger = logging.getLogger(__name__)


def _auto_configure() -> Logger:
    """
    Auto-configure logger from environment variables.

    Attempts to load configuration from environment variables using the
    existing load_config() function. Falls back to local logger if
    configuration fails.

    Returns:
        Logger instance (configured for API or local mode)
    """
    try:
        # Try to load configuration from environment
        config = load_config()
        logger_instance = Logger(config=config)
        logger.debug("Logger auto-configured from environment variables")
        return logger_instance

    except ConfigurationError as e:
        # Configuration error - fall back to local logger
        logger.debug(f"Auto-configuration failed (config error): {e}")
        return _create_local_logger()

    except Exception as e:
        # Any other error - fall back to local logger
        logger.debug(f"Auto-configuration failed (unexpected error): {e}")
        return _create_local_logger()


def _create_config_from_api_key(api_key: str, **kwargs) -> APIConfig:
    """
    Create APIConfig from API key and optional parameters.

    Args:
        api_key: API key string (required)
        **kwargs: Optional configuration overrides:
            - base_url: Override default base URL
            - environment: Override environment (development/staging/production)
            - timeouts: Override timeout configuration
            - retry_strategy: Override retry strategy

    Returns:
        APIConfig object with provided parameters and defaults

    Raises:
        ValueError: If api_key is invalid
        ConfigurationError: If configuration cannot be created
    """
    if not api_key or not isinstance(api_key, str):
        raise ValueError("API key must be a non-empty string")

    # Sanitize API key
    api_key = api_key.strip()
    if not api_key:
        raise ValueError("API key cannot be empty or whitespace only")

    try:
        # Determine base URL
        base_url = kwargs.get('base_url')
        if not base_url:
            base_url = os.getenv('BASELOG_API_BASE_URL', 'https://baselog-api.vercel.app')

        # Determine environment
        environment_str = kwargs.get('environment')
        if not environment_str:
            environment_str = os.getenv('BASELOG_ENVIRONMENT', 'development')

        try:
            environment = Environment(environment_str)
        except ValueError:
            raise ConfigurationError(f"Invalid environment: {environment_str}")

        # Load timeouts (from kwargs, env vars, or defaults)
        timeouts = kwargs.get('timeouts')
        if timeouts is None:
            timeouts = Timeouts.from_env()

        # Load retry strategy (from kwargs, env vars, or defaults)
        retry_strategy = kwargs.get('retry_strategy')
        if retry_strategy is None:
            retry_strategy = RetryStrategy.from_env()

        # Create and return configuration
        config = APIConfig(
            api_key=api_key,
            base_url=base_url,
            environment=environment,
            timeouts=timeouts,
            retry_strategy=retry_strategy,
            batch_size=kwargs.get('batch_size', 100),
            batch_interval=kwargs.get('batch_interval', 5)
        )

        logger.debug(f"Configuration created from API key for environment: {environment.value}")
        return config

    except Exception as e:
        if isinstance(e, (ValueError, ConfigurationError)):
            raise
        raise ConfigurationError(f"Failed to create configuration from API key: {e}")


def _create_local_logger() -> Logger:
    """
    Create a local-only logger instance.

    Returns:
        Logger instance configured for local logging only
    """
    logger_instance = Logger()
    logger.debug("Local logger created (no API configuration)")
    return logger_instance


def _validate_api_key(api_key: str) -> str:
    """
    Validate and sanitize API key.

    Args:
        api_key: Raw API key string

    Returns:
        Sanitized API key

    Raises:
        ValueError: If API key is invalid
    """
    if not api_key:
        raise ValueError("API key is required")

    if not isinstance(api_key, str):
        raise ValueError("API key must be a string")

    # Sanitize
    sanitized = api_key.strip()

    if not sanitized:
        raise ValueError("API key cannot be empty or whitespace only")

    if len(sanitized) < 16:
        raise ValueError("API key must be at least 16 characters long")

    return sanitized


def _get_environment_config() -> dict:
    """
    Get configuration values from environment variables.

    Returns:
        Dictionary with environment configuration
    """
    return {
        'api_key': os.getenv('BASELOG_API_KEY'),
        'base_url': os.getenv('BASELOG_API_BASE_URL', 'https://baselog-api.vercel.app'),
        'environment': os.getenv('BASELOG_ENVIRONMENT', 'development'),
        'timeout_connect': os.getenv('BASELOG_TIMEOUT_CONNECT', '10.0'),
        'timeout_read': os.getenv('BASELOG_TIMEOUT_READ', '30.0'),
        'timeout_write': os.getenv('BASELOG_TIMEOUT_WRITE', '30.0'),
        'timeout_pool': os.getenv('BASELOG_TIMEOUT_POOL', '60.0'),
        'retry_count': os.getenv('BASELOG_RETRY_COUNT', '3'),
        'retry_backoff': os.getenv('BASELOG_RETRY_BACKOFF', '1.0'),
        'batch_size': os.getenv('BASELOG_BATCH_SIZE', '100'),
        'batch_interval': os.getenv('BASELOG_BATCH_INTERVAL', '5')
    }


def _log_configuration_info(config: APIConfig) -> None:
    """
    Log configuration information for debugging (with masked API key).

    Args:
        config: APIConfig instance to log
    """
    masked_key = config.api_key[:4] + "..." + config.api_key[-4:] if len(config.api_key) > 8 else "***"

    logger.info(f"Logger configured - Base URL: {config.base_url}, Environment: {config.environment.value}, API Key: {masked_key}")