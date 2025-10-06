import pytest
from unittest.mock import Mock, patch, AsyncMock
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from baselog.logger import Logger, LoggerMode


class TestLoggerMode:
    """Test cases for the LoggerMode enum."""

    def test_logger_mode_values(self):
        """Test that LoggerMode enum has correct values."""
        assert LoggerMode.LOCAL.value == "local"
        assert LoggerMode.API.value == "api"

    def test_logger_mode_string_representation(self):
        """Test string representation of LoggerMode."""
        assert str(LoggerMode.LOCAL) == "local"
        assert str(LoggerMode.API) == "api"

    def test_logger_mode_repr_representation(self):
        """Test repr representation of LoggerMode."""
        assert repr(LoggerMode.LOCAL) == "LoggerMode.LOCAL"
        assert repr(LoggerMode.API) == "LoggerMode.API"

    def test_logger_mode_comparison(self):
        """Test LoggerMode comparison operations."""
        assert LoggerMode.LOCAL == LoggerMode.LOCAL
        assert LoggerMode.API == LoggerMode.API
        assert LoggerMode.LOCAL != LoggerMode.API

    def test_logger_mode_membership(self):
        """Test LoggerMode membership in enum."""
        assert LoggerMode.LOCAL in LoggerMode
        assert LoggerMode.API in LoggerMode


class TestLogger:
    """Test cases for the Logger class."""

    def test_logger_default_local_mode(self):
        """Test that logger defaults to LOCAL mode."""
        logger = Logger()
        assert logger.mode == LoggerMode.LOCAL
        assert logger.is_local_mode()
        assert not logger.is_api_mode()

    @patch('baselog.api.client.APIClient')
    @patch('baselog.api.config.APIConfig')
    def test_logger_api_mode_with_api_key(self, mock_api_config, mock_api_client):
        """Test logger switches to API mode when api_key is provided."""
        mock_config_instance = Mock()
        mock_client_instance = Mock()
        mock_api_config.return_value = mock_config_instance
        mock_api_client.return_value = mock_client_instance

        logger = Logger(api_key="test-api-key")

        assert logger.mode == LoggerMode.API
        assert logger.is_api_mode()
        assert not logger.is_local_mode()
        mock_api_config.assert_called_once_with(api_key="test-api-key")
        mock_api_client.assert_called_once_with(mock_config_instance)

    @patch('baselog.api.client.APIClient')
    @patch('baselog.api.config.APIConfig')
    def test_logger_api_mode_with_config(self, mock_api_config, mock_api_client):
        """Test logger switches to API mode when config is provided."""
        mock_config = Mock()
        mock_client_instance = Mock()
        mock_api_config.return_value = Mock()  # Mock APIConfig too
        mock_api_client.return_value = mock_client_instance

        logger = Logger(config=mock_config)

        assert logger.mode == LoggerMode.API
        assert logger.is_api_mode()
        assert not logger.is_local_mode()
        mock_api_client.assert_called_once_with(mock_config)

    @patch('baselog.api.client.APIClient')
    @patch('baselog.api.config.APIConfig')
    def test_logger_fallback_to_local_on_error(self, mock_api_config, mock_api_client):
        """Test logger falls back to LOCAL mode on API setup error."""
        # Make APIClient constructor raise an exception
        mock_api_client.side_effect = Exception("Setup failed")
        # Ensure APIConfig doesn't raise an exception
        mock_api_config.return_value = Mock()

        logger = Logger(api_key="test-api-key")

        assert logger.mode == LoggerMode.LOCAL
        assert logger.is_local_mode()
        assert not logger.is_api_mode()

    def test_logger_mode_property(self):
        """Test mode property returns correct LoggerMode."""
        logger = Logger()
        assert isinstance(logger.mode, LoggerMode)
        assert logger.mode == LoggerMode.LOCAL

    @patch('baselog.api.client.APIClient')
    @patch('baselog.api.config.APIConfig')
    def test_logger_mode_switching_on_successful_setup(self, mock_api_config, mock_api_client):
        """Test mode switching to API mode on successful setup."""
        mock_config_instance = Mock()
        mock_client_instance = Mock()
        mock_api_config.return_value = mock_config_instance
        mock_api_client.return_value = mock_client_instance

        logger = Logger(api_key="test-api-key")

        assert logger.mode == LoggerMode.API
        assert logger.mode != LoggerMode.LOCAL

    @patch('baselog.api.client.APIClient')
    @patch('baselog.api.config.APIConfig')
    def test_logger_mode_switching_on_failed_setup(self, mock_api_config, mock_api_client):
        """Test mode remains LOCAL on failed setup."""
        # Make APIClient constructor raise an exception
        mock_api_client.side_effect = Exception("Network error")
        # Ensure APIConfig doesn't raise an exception
        mock_api_config.return_value = Mock()

        logger = Logger(api_key="test-api-key")

        assert logger.mode == LoggerMode.LOCAL
        assert logger.mode != LoggerMode.API

    @patch('baselog.api.client.APIClient')
    @patch('baselog.api.config.APIConfig')
    @patch('builtins.print')
    def test_logger_methods_local_mode(self, mock_print, mock_api_config, mock_api_client):
        """Test logger methods work in local mode."""
        # Mock APIClient to raise exception to force local mode
        mock_api_client.side_effect = Exception("Setup failed")
        mock_api_config.return_value = Mock()

        logger = Logger(api_key="test-api-key")

        logger.info("Test info message", category="test", tags=["tag1", "tag2"])
        logger.debug("Test debug message")
        logger.warning("Test warning message")
        logger.error("Test error message")
        logger.critical("Test critical message")

        # Verify print calls
        assert mock_print.call_count == 5
        mock_print.assert_any_call("Test info message", "test", ["tag1", "tag2"])
        mock_print.assert_any_call("Test debug message", None, [])
        mock_print.assert_any_call("Test warning message", None, [])
        mock_print.assert_any_call("Test error message", None, [])
        mock_print.assert_any_call("Test critical message", None, [])

    @patch('baselog.api.client.APIClient')
    @patch('baselog.api.config.APIConfig')
    @patch('builtins.print')
    def test_logger_methods_api_mode(self, mock_print, mock_api_config, mock_api_client):
        """Test logger methods work in API mode."""
        mock_config_instance = Mock()
        mock_client_instance = Mock()
        mock_api_config.return_value = mock_config_instance
        mock_api_client.return_value = mock_client_instance

        logger = Logger(api_key="test-api-key")

        logger.info("API info message", category="api", tags=["api-tag"])
        logger.debug("API debug message")

        # Verify API mode prefix is added to print output
        mock_print.assert_any_call("API mode: API info message", "api", ["api-tag"])
        mock_print.assert_any_call("API mode: API debug message", None, [])

    def test_logger_without_credentials_stays_local(self):
        """Test logger stays in local mode when no credentials provided."""
        logger = Logger()
        assert logger.mode == LoggerMode.LOCAL
        assert logger.is_local_mode()

    @patch('baselog.api.client.APIClient')
    @patch('baselog.api.config.APIConfig')
    def test_logger_api_client_creation_with_different_configs(self, mock_api_config, mock_api_client):
        """Test API client creation with different configurations."""
        mock_config1 = Mock()
        mock_config2 = Mock()
        mock_client_instance = Mock()
        mock_api_client.return_value = mock_client_instance

        # Test with first config
        logger1 = Logger(config=mock_config1)
        assert logger1.mode == LoggerMode.API
        mock_api_client.assert_called_with(mock_config1)

        # Test with second config
        logger2 = Logger(config=mock_config2)
        assert logger2.mode == LoggerMode.API
        mock_api_client.assert_called_with(mock_config2)

    @patch('baselog.api.client.APIClient')
    @patch('baselog.api.config.APIConfig')
    def test_logger_exception_types_caused_fallback(self, mock_api_config, mock_api_client):
        """Test various exception types cause fallback to local mode."""
        # Test with different exception types
        exceptions = [
            ValueError("Invalid API key"),
            ConnectionError("Network failed"),
            TimeoutError("Connection timeout"),
            RuntimeError("Unexpected error")
        ]

        for exc in exceptions:
            # Reset side effects for each iteration
            mock_api_client.side_effect = exc
            mock_api_config.return_value = Mock()

            logger = Logger(api_key="test-api-key")
            assert logger.mode == LoggerMode.LOCAL, f"Failed to fallback with {exc.__class__.__name__}"

    def test_logger_mode_immutability(self):
        """Test that LoggerMode enum values are immutable."""
        # This is more of a conceptual test - enum values should be immutable
        mode = LoggerMode.LOCAL
        assert mode.value == "local"  # Test value access
        assert str(mode) == "local"  # Test string conversion
        assert repr(mode) == "LoggerMode.LOCAL"  # Test repr conversion