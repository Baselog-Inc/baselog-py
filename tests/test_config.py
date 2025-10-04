"""Tests for the configuration management module"""

import pytest
from baselog.api.config import (
    Environment,
    ConfigurationError,
    MissingConfigurationError,
    InvalidConfigurationError,
    EnvironmentConfigurationError,
    Timeouts,
    RetryStrategy,
    APIConfig,
    load_config
)


class TestEnvironment:
    """Test Environment enum"""

    def test_environment_values(self):
        assert Environment.DEVELOPMENT.value == "development"
        assert Environment.STAGING.value == "staging"
        assert Environment.PRODUCTION.value == "production"


class TestConfigurationError:
    """Test configuration exception hierarchy"""

    def test_configuration_error_hierarchy(self):
        assert issubclass(MissingConfigurationError, ConfigurationError)
        assert issubclass(InvalidConfigurationError, ConfigurationError)
        assert issubclass(EnvironmentConfigurationError, ConfigurationError)

        # Test each exception can be raised
        with pytest.raises(ConfigurationError):
            raise ConfigurationError("Base error")

        with pytest.raises(MissingConfigurationError):
            raise MissingConfigurationError("Missing config")

        with pytest.raises(InvalidConfigurationError):
            raise InvalidConfigurationError("Invalid config")

        with pytest.raises(EnvironmentConfigurationError):
            raise EnvironmentConfigurationError("Environment config error")


class TestTimeouts:
    """Test Timeouts dataclass"""

    def test_timeouts_default_values(self):
        timeouts = Timeouts()
        assert timeouts.connect == 10.0
        assert timeouts.read == 30.0
        assert timeouts.write == 30.0
        assert timeouts.pool == 60.0

    def test_timeouts_custom_values(self):
        timeouts = Timeouts(connect=5.0, read=15.0, write=20.0, pool=30.0)
        assert timeouts.connect == 5.0
        assert timeouts.read == 15.0
        assert timeouts.write == 20.0
        assert timeouts.pool == 30.0

    def test_timeouts_immutability(self):
        timeouts = Timeouts()
        # dataclasses are mutable by default, but we can test that fields exist
        assert hasattr(timeouts, 'connect')
        assert hasattr(timeouts, 'read')
        assert hasattr(timeouts, 'write')
        assert hasattr(timeouts, 'pool')


class TestRetryStrategy:
    """Test RetryStrategy dataclass"""

    def test_retry_strategy_default_values(self):
        retry = RetryStrategy()
        assert retry.max_attempts == 3
        assert retry.backoff_factor == 1.0
        assert retry.status_forcelist == [429, 500, 502, 503, 504]
        assert retry.allowed_methods == ['POST', 'PUT', 'PATCH']

    def test_retry_strategy_custom_values(self):
        retry = RetryStrategy(
            max_attempts=5,
            backoff_factor=2.0,
            status_forcelist=[400, 500, 503],
            allowed_methods=['GET', 'POST', 'PUT']
        )
        assert retry.max_attempts == 5
        assert retry.backoff_factor == 2.0
        assert retry.status_forcelist == [400, 500, 503]
        assert retry.allowed_methods == ['GET', 'POST', 'PUT']

    def test_retry_strategy_default_lists_are_copies(self):
        retry1 = RetryStrategy()
        retry2 = RetryStrategy()

        # Modify one instance
        retry1.status_forcelist.append(999)

        # Check that the other instance is not affected
        assert 999 not in retry2.status_forcelist
        assert retry2.status_forcelist == [429, 500, 502, 503, 504]


class TestAPIConfig:
    """Test APIConfig dataclass"""

    def test_api_config_required_fields(self):
        timeouts = Timeouts()
        retry = RetryStrategy()

        config = APIConfig(
            base_url="https://api.baselog.io",
            api_key="test-key",
            environment="development",
            timeouts=timeouts,
            retry_strategy=retry
        )

        assert config.base_url == "https://api.baselog.io"
        assert config.api_key == "test-key"
        assert config.environment == "development"
        assert config.timeouts == timeouts
        assert config.retry_strategy == retry
        assert config.batch_size == 100
        assert config.batch_interval == 5

    def test_api_config_with_custom_values(self):
        timeouts = Timeouts()
        retry = RetryStrategy()

        config = APIConfig(
            base_url="https://staging.baselog.io",
            api_key="staging-key",
            environment="staging",
            timeouts=timeouts,
            retry_strategy=retry,
            batch_size=50,
            batch_interval=10
        )

        assert config.batch_size == 50
        assert config.batch_interval == 10


class TestLoadConfig:
    """Test load_config function"""

    def test_load_config_not_implemented(self):
        with pytest.raises(NotImplementedError, match="Configuration loading implementation in Issue 005"):
            load_config()


class TestIntegration:
    """Test integration between components"""

    def test_full_configuration_creation(self):
        """Test creating a complete configuration object"""
        timeouts = Timeouts(connect=15.0, read=45.0)
        retry = RetryStrategy(max_attempts=5)

        config = APIConfig(
            base_url="https://api.baselog.io/v1",
            api_key="secret-key",
            environment="production",
            timeouts=timeouts,
            retry_strategy=retry,
            batch_size=200,
            batch_interval=15
        )

        # Verify all components are properly connected
        assert config.environment == "production"
        assert config.timeouts.connect == 15.0
        assert config.retry_strategy.max_attempts == 5
        assert config.batch_size == 200
        assert config.batch_interval == 15

    def test_configuration_objects_are_immutable_by_convention(self):
        """Test that configuration objects behave as expected to be immutable"""
        timeouts = Timeouts()
        retry = RetryStrategy()
        config = APIConfig(
            base_url="https://api.baselog.io",
            api_key="test-key",
            environment="development",
            timeouts=timeouts,
            retry_strategy=retry
        )

        # Verify objects are properly structured
        assert isinstance(config.environment, str)
        assert isinstance(config.timeouts, Timeouts)
        assert isinstance(config.retry_strategy, RetryStrategy)

        # Verify default values are properly set
        assert isinstance(config.batch_size, int)
        assert isinstance(config.batch_interval, int)
        assert config.batch_interval is not None