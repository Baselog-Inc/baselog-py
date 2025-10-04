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
    pass


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


@dataclass
class RetryStrategy:
    """Retry strategy configuration"""
    max_attempts: int = 3
    backoff_factor: float = 1.0
    status_forcelist: List[int] = field(default_factory=lambda: [429, 500, 502, 503, 504])
    allowed_methods: List[str] = field(default_factory=lambda: ['POST', 'PUT', 'PATCH'])


@dataclass
class APIConfig:
    """Main configuration object for the Baselog API client"""
    base_url: str
    api_key: str
    environment: str
    timeouts: Timeouts
    retry_strategy: RetryStrategy
    batch_size: int = 100
    batch_interval: Optional[int] = 5


def load_config() -> APIConfig:
    """Load and validate the full configuration"""
    # Implementation will be added in Issue 005
    raise NotImplementedError("Configuration loading implementation in Issue 005")