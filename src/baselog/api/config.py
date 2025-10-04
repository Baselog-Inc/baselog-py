"""
Configuration Management System for Baselog API Client

This module provides centralized, type-safe configuration management
for the entire baselog SDK.
"""

import os
from dataclasses import dataclass, field
from typing import Optional, List
from enum import Enum


class Environment(Enum):
    """Supported deployment environments"""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


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


@dataclass
class Timeouts:
    """HTTP timeouts configuration"""
    connect: float = 10.0
    read: float = 30.0
    write: float = 30.0
    pool: float = 60.0

    @classmethod
    def from_env(cls) -> 'Timeouts':
        """Load timeouts from environment variables"""
        try:
            return cls(
                connect=float(os.getenv("BASELOG_TIMEOUT_CONNECT", "10.0")),
                read=float(os.getenv("BASELOG_TIMEOUT_READ", "30.0")),
                write=float(os.getenv("BASELOG_TIMEOUT_WRITE", "30.0")),
                pool=float(os.getenv("BASELOG_TIMEOUT_POOL", "60.0"))
            )
        except ValueError as e:
            raise InvalidConfigurationError(f"Invalid timeout value: {e}")

    def to_dict(self) -> dict:
        """Convert to dict format for httpx.Timeout"""
        return {k: getattr(self, k) for k in self.__dataclass_fields__}


@dataclass
class RetryStrategy:
    """Retry strategy configuration"""
    max_attempts: int = 3
    backoff_factor: float = 1.0
    status_forcelist: List[int] = field(default_factory=lambda: [429, 500, 502, 503, 504])
    allowed_methods: List[str] = field(default_factory=lambda: ['POST', 'PUT', 'PATCH'])

    @classmethod
    def from_env(cls) -> 'RetryStrategy':
        """Load retry strategy from environment variables"""
        try:
            return cls(
                max_attempts=int(os.getenv("BASELOG_RETRY_COUNT", "3")),
                backoff_factor=float(os.getenv("BASELOG_RETRY_BACKOFF", "1.0")),
                status_forcelist=cls._parse_status_list(os.getenv("BASELOG_RETRY_STATUS_CODES", "")),
                allowed_methods=cls._parse_method_list(os.getenv("BASELOG_RETRY_METHODS", ""))
            )
        except ValueError as e:
            raise InvalidConfigurationError(f"Invalid retry configuration: {e}")

    @staticmethod
    def _parse_status_list(value: str) -> List[int]:
        """Parse comma-separated status codes"""
        if not value:
            return [429, 500, 502, 503, 504]
        try:
            return [int(code.strip()) for code in value.split(",")]
        except ValueError:
            raise InvalidConfigurationError(f"Invalid status codes: {value}")

    @staticmethod
    def _parse_method_list(value: str) -> List[str]:
        """Parse comma-separated HTTP methods"""
        if not value:
            return ['POST', 'PUT', 'PATCH']
        return [method.strip().upper() for method in value.split(",")]

    def to_dict(self) -> dict:
        """Convert to dict format for tenacity"""
        return {k: getattr(self, k) for k in self.__dataclass_fields__}


@dataclass
class APIConfig:
    """Main configuration object for the Baselog API client"""
    base_url: str
    api_key: str
    environment: Environment
    timeouts: Timeouts
    retry_strategy: RetryStrategy
    batch_size: int = 100
    batch_interval: Optional[int] = None


def load_config() -> APIConfig:
    """Load and validate the full configuration from environment variables"""
    try:
        # Load basic configuration
        base_url = os.getenv("BASELOG_API_BASE_URL")
        if not base_url:
            base_url = "https://api.baselog.io/v1"

        api_key = os.getenv("BASELOG_API_KEY")
        if not api_key:
            raise MissingConfigurationError("BASELOG_API_KEY is required")

        environment_str = os.getenv("BASELOG_ENVIRONMENT", "development")
        try:
            environment = Environment(environment_str)
        except ValueError:
            raise InvalidConfigurationError(
                f"Invalid environment: {environment_str}. Must be one of {[e.value for e in Environment]}"
            )

        # Load structured components
        try:
            timeouts = Timeouts.from_env()
            retry_strategy = RetryStrategy.from_env()
        except InvalidConfigurationError as e:
            raise EnvironmentConfigurationError(f"Environment configuration failed: {e}")

        # Validate batch configuration (if provided)
        batch_size = int(os.getenv("BASELOG_BATCH_SIZE", "100"))
        batch_interval = os.getenv("BASELOG_BATCH_INTERVAL")

        if batch_size <= 0:
            raise InvalidConfigurationError("Batch size must be positive")

        return APIConfig(
            base_url=base_url,
            api_key=api_key,
            environment=environment,
            timeouts=timeouts,
            retry_strategy=retry_strategy,
            batch_size=batch_size,
            batch_interval=int(batch_interval) if batch_interval else None
        )

    except ValueError as e:
        raise InvalidConfigurationError(f"Configuration value error: {e}")
    except Exception as e:
        if isinstance(e, ConfigurationError):
            raise
        raise ConfigurationError(f"Unexpected configuration error: {e}")