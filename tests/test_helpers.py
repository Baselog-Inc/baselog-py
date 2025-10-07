"""Tests for helper functions in src/baselog/helpers.py"""

import pytest
import os
from unittest.mock import patch, MagicMock, mock_open

from baselog.helpers import (
    _auto_configure,
    _create_config_from_api_key,
    _create_local_logger,
    _validate_api_key,
    _get_environment_config,
    _log_configuration_info
)
from baselog.logger import Logger
from baselog.api.config import APIConfig, Timeouts, RetryStrategy, Environment
from baselog.api.exceptions import ConfigurationError


class TestAutoConfigure:
    """Test cases for _auto_configure function."""

    def test_auto_configure_with_valid_config(self):
        """Test auto-configuration with valid environment variables."""
        with patch('baselog.api.config.load_config') as mock_load_config:
            mock_config = MagicMock()
            mock_load_config.return_value = mock_config

            with patch('baselog.logger.Logger') as mock_logger_class:
                mock_logger_instance = MagicMock()
                mock_logger_class.return_value = mock_logger_instance

                result = _auto_configure()

                assert isinstance(result, Logger)
                mock_load_config.assert_called_once()
                assert result.config == mock_config

    def test_auto_configure_config_error_fallback(self):
        """Test auto-configuration falls back to local logger on config error."""
        with patch('baselog.api.config.load_config') as mock_load_config, \
             patch('baselog.helpers._create_local_logger') as mock_create_local:
            mock_load_config.side_effect = ConfigurationError("Invalid config")
            mock_create_local.return_value = MagicMock()

            result = _auto_configure()

            assert isinstance(result, Logger)
            mock_load_config.assert_called_once()
            mock_create_local.assert_called_once()

    def test_auto_configure_unexpected_error_fallback(self):
        """Test auto-configuration falls back to local logger on unexpected error."""
        with patch('baselog.api.config.load_config') as mock_load_config, \
             patch('baselog.helpers._create_local_logger') as mock_create_local:
            mock_load_config.side_effect = Exception("Unexpected error")
            mock_create_local.return_value = MagicMock()

            result = _auto_configure()

            assert isinstance(result, Logger)
            mock_load_config.assert_called_once()
            mock_create_local.assert_called_once()


class TestCreateConfigFromApiKey:
    """Test cases for _create_config_from_api_key function."""

    def test_create_config_with_minimal_parameters(self):
        """Test config creation with just API key."""
        api_key = "test_api_key_1234567890123456"

        with patch('baselog.api.config.Timeouts') as mock_timeouts, \
             patch('baselog.api.config.RetryStrategy') as mock_retry_strategy, \
             patch('baselog.api.config.Environment') as mock_env:

            mock_timeouts.from_env.return_value = MagicMock()
            mock_retry_strategy.from_env.return_value = MagicMock()
            mock_env.return_value = MagicMock(Environment="development")

            result = _create_config_from_api_key(api_key)

            assert isinstance(result, APIConfig)
            assert result.api_key == api_key

    def test_create_config_with_overrides(self):
        """Test config creation with parameter overrides."""
        api_key = "test_api_key_1234567890123456"
        base_url = "https://custom.api.com/v1"
        environment = "production"

        with patch('baselog.api.config.Timeouts') as mock_timeouts, \
             patch('baselog.api.config.RetryStrategy') as mock_retry_strategy, \
             patch('baselog.api.config.Environment') as mock_env:

            mock_timeouts.from_env.return_value = MagicMock()
            mock_retry_strategy.from_env.return_value = MagicMock()
            mock_env.return_value = MagicMock(Environment=environment)

            result = _create_config_from_api_key(
                api_key,
                base_url=base_url,
                environment=environment
            )

            assert result.api_key == api_key
            assert result.base_url == base_url
            assert result.environment.value == environment

    def test_create_config_invalid_api_key(self):
        """Test config creation with invalid API key."""
        with pytest.raises(ValueError, match="API key must be a non-empty string"):
            _create_config_from_api_key("")

        with pytest.raises(ValueError, match="API key must be a non-empty string"):
            _create_config_from_api_key(None)

        with pytest.raises(ValueError, match="API key cannot be empty or whitespace only"):
            _create_config_from_api_key("   ")

    def test_create_config_invalid_environment(self):
        """Test config creation with invalid environment."""
        with patch('baselog.api.config.Environment') as mock_env:
            mock_env.side_effect = ValueError("Invalid environment")

            with pytest.raises(ConfigurationError, match="Invalid environment"):
                _create_config_from_api_key("valid_api_key", environment="invalid_env")

    def test_create_config_from_environment_variables(self):
        """Test config creation uses environment variables when not provided."""
        api_key = "test_api_key_1234567890123456"

        with patch.dict(os.environ, {
            'BASELOG_API_BASE_URL': 'https://env.api.com/v1',
            'BASELOG_ENVIRONMENT': 'staging'
        }):
            with patch('baselog.api.config.Timeouts') as mock_timeouts, \
                 patch('baselog.api.config.RetryStrategy') as mock_retry_strategy, \
                 patch('baselog.api.config.Environment') as mock_env:

                mock_timeouts.from_env.return_value = MagicMock()
                mock_retry_strategy.from_env.return_value = MagicMock()
                mock_env.return_value = MagicMock(Environment="staging")

                result = _create_config_from_api_key(api_key)

                assert result.base_url == 'https://env.api.com/v1'
                assert result.environment.value == 'staging'


class TestCreateLocalLogger:
    """Test cases for _create_local_logger function."""

    def test_create_local_logger(self):
        """Test local logger creation."""
        result = _create_local_logger()

        assert isinstance(result, Logger)


class TestValidateApiKey:
    """Test cases for _validate_api_key function."""

    def test_validate_api_key_valid(self):
        """Test validation of valid API key."""
        api_key = "  valid_api_key_1234567890123456  "

        result = _validate_api_key(api_key)

        assert result == api_key.strip()

    def test_validate_api_key_invalid_empty(self):
        """Test validation fails for empty API key."""
        with pytest.raises(ValueError, match="API key is required"):
            _validate_api_key("")

    def test_validate_api_key_invalid_type(self):
        """Test validation fails for non-string API key."""
        with pytest.raises(ValueError, match="API key must be a string"):
            _validate_api_key(None)

        with pytest.raises(ValueError, match="API key must be a string"):
            _validate_api_key(123)

    def test_validate_api_key_invalid_whitespace(self):
        """Test validation fails for whitespace-only API key."""
        with pytest.raises(ValueError, match="API key cannot be empty or whitespace only"):
            _validate_api_key("   ")

    def test_validate_api_key_too_short(self):
        """Test validation fails for API key too short."""
        with pytest.raises(ValueError, match="API key must be at least 16 characters long"):
            _validate_api_key("short")


class TestGetEnvironmentConfig:
    """Test cases for _get_environment_config function."""

    def test_get_environment_config_defaults(self):
        """Test environment config returns default values."""
        with patch.dict(os.environ, {}, clear=True):
            result = _get_environment_config()

            expected = {
                'api_key': None,
                'base_url': 'https://baselog-api.vercel.app',
                'environment': 'development',
                'timeout_connect': '10.0',
                'timeout_read': '30.0',
                'timeout_write': '30.0',
                'timeout_pool': '60.0',
                'retry_count': '3',
                'retry_backoff': '1.0',
                'batch_size': '100',
                'batch_interval': '5'
            }

            assert result == expected

    def test_get_environment_config_with_values(self):
        """Test environment config with actual values."""
        env_values = {
            'BASELOG_API_KEY': 'test_key',
            'BASELOG_API_BASE_URL': 'https://custom.api.com/v1',
            'BASELOG_ENVIRONMENT': 'production',
            'BASELOG_TIMEOUT_CONNECT': '5.0',
            'BASELOG_TIMEOUT_READ': '10.0'
        }

        with patch.dict(os.environ, env_values):
            result = _get_environment_config()

            expected = {
                'api_key': 'test_key',
                'base_url': 'https://custom.api.com/v1',
                'environment': 'production',
                'timeout_connect': '5.0',
                'timeout_read': '10.0',
                'timeout_write': '30.0',  # defaults
                'timeout_pool': '60.0',  # defaults
                'retry_count': '3',  # defaults
                'retry_backoff': '1.0',  # defaults
                'batch_size': '100',  # defaults
                'batch_interval': '5'  # defaults
            }

            assert result == expected


class TestLogConfigurationInfo:
    """Test cases for _log_configuration_info function."""

    def test_log_configuration_info_masks_api_key(self):
        """Test configuration info logging masks API key."""
        config = MagicMock()
        config.api_key = "full_api_key_1234567890123456"
        config.base_url = "https://baselog-api.vercel.app"
        config.environment = MagicMock(Environment="development")

        with patch('baselog.helpers.logger') as mock_logger:
            _log_configuration_info(config)

            mock_logger.info.assert_called_once()
            # Check that the call contains the masked API key (remove the extra dot)
            call_args = mock_logger.info.call_args[0][0]
            assert "full...3456" in call_args
            assert "Base URL: https://baselog-api.vercel.app" in call_args
            assert "Environment: development" in call_args

    def test_log_configuration_info_short_api_key(self):
        """Test configuration info logging with short API key."""
        config = MagicMock()
        config.api_key = "short123"
        config.base_url = "https://baselog-api.vercel.app"
        config.environment = MagicMock(value="development")

        with patch('baselog.helpers.logger') as mock_logger:
            _log_configuration_info(config)

            mock_logger.info.assert_called_once_with(
                "Logger configured - Base URL: https://baselog-api.vercel.app, Environment: development, API Key: ***"
            )


class TestIntegrationScenarios:
    """Integration test scenarios for helper functions."""

    def test_end_to_end_config_creation(self):
        """Test complete flow of config creation and usage."""
        api_key = "test_api_key_1234567890123456"

        with patch('baselog.api.config.Timeouts') as mock_timeouts, \
             patch('baselog.api.config.RetryStrategy') as mock_retry_strategy, \
             patch('baselog.api.config.Environment') as mock_env:

            mock_timeouts.from_env.return_value = MagicMock()
            mock_retry_strategy.from_env.return_value = MagicMock()
            mock_env.return_value = MagicMock(Environment="development")

            # Create config
            config = _create_config_from_api_key(api_key)

            # Validate config
            assert config.api_key == api_key
            assert config.environment.value == "development"

            # Test logging
            _log_configuration_info(config)

            # Test validation
            validated_key = _validate_api_key(api_key)
            assert validated_key == api_key

    def test_error_handling_chain(self):
        """Test error handling works across multiple functions."""
        # Test invalid API key propagates correctly
        with pytest.raises(ValueError, match="API key must be a non-empty string"):
            _create_config_from_api_key("")

        # Test invalid environment converts to ConfigurationError
        with pytest.raises(ConfigurationError):
            _create_config_from_api_key("valid_api_key", environment="invalid_env")

    def test_environment_variable_hierarchy(self):
        """Test that environment variables take proper precedence."""
        api_key = "test_key_1234567890123456"
        env_base_url = "https://env.api.com/v1"
        override_base_url = "https://override.api.com/v1"

        with patch.dict(os.environ, {'BASELOG_API_BASE_URL': env_base_url}):
            with patch('baselog.api.config.Timeouts') as mock_timeouts, \
                 patch('baselog.api.config.RetryStrategy') as mock_retry_strategy, \
                 patch('baselog.api.config.Environment') as mock_env:

                mock_timeouts.from_env.return_value = MagicMock()
                mock_retry_strategy.from_env.return_value = MagicMock()
                mock_env.return_value = MagicMock(Environment="development")

                # Priority: override > env > default
                result = _create_config_from_api_key(
                    api_key,
                    base_url=override_base_url
                )

                assert result.base_url == override_base_url

                # Test without override (should use env)
                result2 = _create_config_from_api_key(api_key)
                assert result2.base_url == env_base_url