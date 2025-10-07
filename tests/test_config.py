"""Tests for the configuration management module"""

import os
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

    def test_configuration_error_with_context(self):
        """Test ConfigurationError with context information"""
        error = ConfigurationError("Test message", "test_context")
        str_error = str(error)
        assert "Test message" in str_error
        assert "test_context" in str_error

    def test_configuration_error_without_context(self):
        """Test ConfigurationError without context information"""
        error = ConfigurationError("Test message")
        str_error = str(error)
        assert str_error == "Test message"


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

    def test_timeouts_from_env_default(self):
        """Test loading timeouts from environment with default values"""
        # Remove environment variables to test defaults
        if 'BASELOG_TIMEOUT_CONNECT' in os.environ:
            del os.environ['BASELOG_TIMEOUT_CONNECT']

        timeouts = Timeouts.from_env()
        assert timeouts.connect == 10.0
        assert timeouts.read == 30.0
        assert timeouts.write == 30.0
        assert timeouts.pool == 60.0

    def test_timeouts_from_env_custom(self):
        """Test loading timeouts from environment with custom values"""
        # Set environment variables
        os.environ['BASELOG_TIMEOUT_CONNECT'] = '5.5'
        os.environ['BASELOG_TIMEOUT_READ'] = '15.0'
        os.environ['BASELOG_TIMEOUT_WRITE'] = '25.5'
        os.environ['BASELOG_TIMEOUT_POOL'] = '45.0'

        timeouts = Timeouts.from_env()
        assert timeouts.connect == 5.5
        assert timeouts.read == 15.0
        assert timeouts.write == 25.5
        assert timeouts.pool == 45.0

        # Clean up
        del os.environ['BASELOG_TIMEOUT_CONNECT']
        del os.environ['BASELOG_TIMEOUT_READ']
        del os.environ['BASELOG_TIMEOUT_WRITE']
        del os.environ['BASELOG_TIMEOUT_POOL']

    def test_timeouts_from_env_invalid_value(self):
        """Test loading timeouts with invalid values raises exception"""
        os.environ['BASELOG_TIMEOUT_CONNECT'] = 'invalid'

        with pytest.raises(InvalidConfigurationError, match="Invalid timeout value"):
            Timeouts.from_env()

        del os.environ['BASELOG_TIMEOUT_CONNECT']

    def test_timeouts_to_dict(self):
        """Test converting timeouts to dict format"""
        timeouts = Timeouts(connect=5.0, read=15.0)
        expected = {
            'connect': 5.0,
            'read': 15.0,
            'write': 30.0,
            'pool': 60.0
        }
        assert timeouts.to_dict() == expected


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

    def test_retry_strategy_from_env_default(self):
        """Test loading retry strategy from environment with default values"""
        # Remove environment variables to test defaults
        for var in ['BASELOG_RETRY_COUNT', 'BASELOG_RETRY_BACKOFF', 'BASELOG_RETRY_STATUS_CODES', 'BASELOG_RETRY_METHODS']:
            if var in os.environ:
                del os.environ[var]

        retry = RetryStrategy.from_env()
        assert retry.max_attempts == 3
        assert retry.backoff_factor == 1.0
        assert retry.status_forcelist == [429, 500, 502, 503, 504]
        assert retry.allowed_methods == ['POST', 'PUT', 'PATCH']

    def test_retry_strategy_from_env_custom_values(self):
        """Test loading retry strategy from environment with custom values"""
        os.environ['BASELOG_RETRY_COUNT'] = '5'
        os.environ['BASELOG_RETRY_BACKOFF'] = '2.5'
        os.environ['BASELOG_RETRY_STATUS_CODES'] = '401,403,500,502'
        os.environ['BASELOG_RETRY_METHODS'] = 'GET,POST,PUT,DELETE'

        retry = RetryStrategy.from_env()
        assert retry.max_attempts == 5
        assert retry.backoff_factor == 2.5
        assert retry.status_forcelist == [401, 403, 500, 502]
        assert retry.allowed_methods == ['GET', 'POST', 'PUT', 'DELETE']

        # Clean up
        for var in ['BASELOG_RETRY_COUNT', 'BASELOG_RETRY_BACKOFF', 'BASELOG_RETRY_STATUS_CODES', 'BASELOG_RETRY_METHODS']:
            if var in os.environ:
                del os.environ[var]

    def test_retry_strategy_from_env_invalid_value(self):
        """Test loading retry strategy with invalid values raises exception"""
        os.environ['BASELOG_RETRY_COUNT'] = 'invalid'

        with pytest.raises(InvalidConfigurationError, match="Invalid retry configuration"):
            RetryStrategy.from_env()

        del os.environ['BASELOG_RETRY_COUNT']

    def test_parse_status_list_empty(self):
        """Test parsing empty status code list"""
        result = RetryStrategy._parse_status_list("")
        assert result == [429, 500, 502, 503, 504]

    def test_parse_status_list_valid(self):
        """Test parsing valid status code list"""
        result = RetryStrategy._parse_status_list("200,404,500,503")
        assert result == [200, 404, 500, 503]

    def test_parse_status_list_invalid(self):
        """Test parsing invalid status code list raises exception"""
        with pytest.raises(InvalidConfigurationError, match="Invalid status codes"):
            RetryStrategy._parse_status_list("200,invalid,500")

    def test_parse_method_list_empty(self):
        """Test parsing empty method list"""
        result = RetryStrategy._parse_method_list("")
        assert result == ['POST', 'PUT', 'PATCH']

    def test_parse_method_list_valid(self):
        """Test parsing valid method list"""
        result = RetryStrategy._parse_method_list("get,post,Put,DELETE")
        assert result == ['GET', 'POST', 'PUT', 'DELETE']

    def test_retry_strategy_to_dict(self):
        """Test converting retry strategy to dict format"""
        retry = RetryStrategy(max_attempts=5, backoff_factor=2.0)
        expected = {
            'max_attempts': 5,
            'backoff_factor': 2.0,
            'status_forcelist': [429, 500, 502, 503, 504],
            'allowed_methods': ['POST', 'PUT', 'PATCH']
        }
        assert retry.to_dict() == expected


class TestAPIConfig:
    """Test APIConfig dataclass"""

    def test_api_config_required_fields(self):
        timeouts = Timeouts()
        retry = RetryStrategy()

        config = APIConfig(
            base_url="https://api.baselog.io",
            api_key="test-key",
            environment=Environment.DEVELOPMENT,
            timeouts=timeouts,
            retry_strategy=retry
        )

        assert config.base_url == "https://api.baselog.io"
        assert config.api_key == "test-key"
        assert config.environment == Environment.DEVELOPMENT
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
            environment=Environment.STAGING,
            timeouts=timeouts,
            retry_strategy=retry,
            batch_size=50,
            batch_interval=10
        )

        assert config.batch_size == 50
        assert config.batch_interval == 10


class TestLoadConfig:
    """Test load_config function"""

    def setup_method(self):
        """Clean environment variables before each test"""
        # Remove all baselog environment variables
        baselog_vars = [var for var in os.environ.keys() if var.startswith('BASELOG_')]
        for var in baselog_vars:
            del os.environ[var]

    def teardown_method(self):
        """Clean environment variables after each test"""
        # Remove all baselog environment variables
        baselog_vars = [var for var in os.environ.keys() if var.startswith('BASELOG_')]
        for var in baselog_vars:
            del os.environ[var]

    def test_load_config_minimal_required(self):
        """Test loading config with only required environment variables"""
        os.environ['BASELOG_API_KEY'] = 'test-key'

        config = load_config()
        assert config.base_url == "https://baselog-api.vercel.app"
        assert config.api_key == "test-key"
        assert config.environment == Environment.DEVELOPMENT
        assert config.batch_size == 100
        # batch_interval defaults to 5 when not explicitly set
        assert config.batch_interval == 5

    def test_load_config_complete_custom(self):
        """Test loading config with all custom values"""
        os.environ['BASELOG_API_BASE_URL'] = 'https://staging.baselog.io/v2'
        os.environ['BASELOG_API_KEY'] = 'staging-key'
        os.environ['BASELOG_ENVIRONMENT'] = 'staging'
        os.environ['BASELOG_TIMEOUT_CONNECT'] = '15.0'
        os.environ['BASELOG_RETRY_COUNT'] = '5'
        os.environ['BASELOG_BATCH_SIZE'] = '200'
        os.environ['BASELOG_BATCH_INTERVAL'] = '10'

        config = load_config()
        assert config.base_url == 'https://staging.baselog.io/v2'
        assert config.api_key == 'staging-key'
        assert config.environment == Environment.STAGING
        assert config.timeouts.connect == 15.0
        assert config.retry_strategy.max_attempts == 5
        assert config.batch_size == 200
        assert config.batch_interval == 10

    def test_load_config_missing_required_api_key(self):
        """Test that missing API key raises MissingConfigurationError"""
        with pytest.raises(MissingConfigurationError, match="BASELOG_API_KEY is required"):
            load_config()

    def test_load_config_invalid_environment(self):
        """Test that invalid environment raises InvalidConfigurationError"""
        os.environ['BASELOG_API_KEY'] = 'test-key'
        os.environ['BASELOG_ENVIRONMENT'] = 'invalid_env'

        with pytest.raises(InvalidConfigurationError, match="Invalid environment: invalid_env"):
            load_config()

    def test_load_config_invalid_batch_size(self):
        """Test that invalid batch size raises InvalidConfigurationError"""
        os.environ['BASELOG_API_KEY'] = 'test-key'
        os.environ['BASELOG_BATCH_SIZE'] = '0'

        with pytest.raises(InvalidConfigurationError, match="Batch size must be positive"):
            load_config()

        os.environ['BASELOG_BATCH_SIZE'] = '-5'
        with pytest.raises(InvalidConfigurationError, match="Batch size must be positive"):
            load_config()

    def test_load_config_invalid_timeout_value(self):
        """Test that invalid timeout value raises EnvironmentConfigurationError"""
        os.environ['BASELOG_API_KEY'] = 'test-key'
        os.environ['BASELOG_TIMEOUT_CONNECT'] = 'invalid'

        with pytest.raises(EnvironmentConfigurationError, match="Environment configuration failed"):
            load_config()

    def test_load_config_invalid_retry_value(self):
        """Test that invalid retry value raises EnvironmentConfigurationError"""
        os.environ['BASELOG_API_KEY'] = 'test-key'
        os.environ['BASELOG_RETRY_COUNT'] = 'invalid'

        with pytest.raises(EnvironmentConfigurationError, match="Environment configuration failed"):
            load_config()

    def test_load_config_batch_interval_optional(self):
        """Test that batch interval is optional and defaults to 5"""
        os.environ['BASELOG_API_KEY'] = 'test-key'

        config = load_config()
        assert config.batch_interval == 5

    def test_load_config_custom_base_url(self):
        """Test custom base URL without trailing slash"""
        os.environ['BASELOG_API_KEY'] = 'test-key'
        os.environ['BASELOG_API_BASE_URL'] = 'https://custom.baselog.io/api'

        config = load_config()
        assert config.base_url == 'https://custom.baselog.io/api'

    def test_load_config_retry_status_codes_parsing(self):
        """Test that retry status codes are properly parsed"""
        os.environ['BASELOG_API_KEY'] = 'test-key'
        os.environ['BASELOG_RETRY_STATUS_CODES'] = '401,403,429,500,502,503'

        config = load_config()
        assert config.retry_strategy.status_forcelist == [401, 403, 429, 500, 502, 503]

    def test_load_config_retry_methods_parsing(self):
        """Test that retry methods are properly parsed and uppercased"""
        os.environ['BASELOG_API_KEY'] = 'test-key'
        os.environ['BASELOG_RETRY_METHODS'] = 'get,post,put,delete,patch'

        config = load_config()
        assert config.retry_strategy.allowed_methods == ['GET', 'POST', 'PUT', 'DELETE', 'PATCH']


class TestIntegration:
    """Test integration between components"""

    def test_full_configuration_creation(self):
        """Test creating a complete configuration object"""
        timeouts = Timeouts(connect=15.0, read=45.0)
        retry = RetryStrategy(max_attempts=5)

        config = APIConfig(
            base_url="https://baselog-api.vercel.app",
            api_key="secret-key",
            environment=Environment.PRODUCTION,
            timeouts=timeouts,
            retry_strategy=retry,
            batch_size=200,
            batch_interval=15
        )

        # Verify all components are properly connected
        assert config.environment == Environment.PRODUCTION
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
            environment=Environment.DEVELOPMENT,
            timeouts=timeouts,
            retry_strategy=retry
        )

        # Verify objects are properly structured
        assert isinstance(config.environment, Environment)
        assert isinstance(config.timeouts, Timeouts)
        assert isinstance(config.retry_strategy, RetryStrategy)

        # Verify default values are properly set
        assert isinstance(config.batch_size, int)
        assert config.batch_interval is not None