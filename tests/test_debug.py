import pytest
from unittest.mock import patch, MagicMock

def test_debug_configuration_fallback():
    """Debug the configuration fallback issue."""
    from baselog.logger_manager import LoggerManager
    from baselog.helpers import _create_config_from_api_key

    # Reset singleton to ensure clean state
    LoggerManager._instance = None
    manager = LoggerManager()

    with patch('baselog.helpers._create_config_from_api_key') as mock_create_config:
        with patch('baselog.logger.Logger') as mock_logger_class:
            # Create a mock logger that will fail when creating API client
            mock_logger_instance = MagicMock()
            mock_logger_instance.is_api_mode.return_value = False  # Local mode
            mock_logger_class.return_value = mock_logger_instance

            mock_create_config.return_value = MagicMock()

            print("Before configure - _configured:", manager._configured)
            print("Before configure - _logger:", manager._logger)

            manager.configure(api_key='test-key-1234567890123456')

            print("After configure - _configured:", manager._configured)
            print("After configure - _logger:", manager._logger)
            print("Logger is_api_mode:", mock_logger_instance.is_api_mode())

            # Should still create a logger, but in local mode
            assert manager._logger is not None
            # The issue is that _configured is being set to True despite being in local mode
            # Since we're mocking the Logger constructor to return False for is_api_mode,
            # _configured should be set to False
            assert manager._configured is False, f"Expected _configured to be False, got {manager._configured}"
        