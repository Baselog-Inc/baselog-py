import sys
sys.path.insert(0, 'src')
from baselog.logger_manager import LoggerManager
from unittest.mock import patch, MagicMock

# Test the specific issue
manager = LoggerManager()

print("=== Manual Test ===")
print("Before configure - _configured:", manager._configured)
print("Before configure - _logger:", manager._logger)

with patch('baselog.logger.Logger') as mock_logger_class:
    # Create a mock logger that will fail when creating API client
    mock_logger_instance = MagicMock()
    mock_logger_instance.is_api_mode.return_value = False  # Local mode
    mock_logger_class.return_value = mock_logger_instance

    print("Mock logger is_api_mode:", mock_logger_instance.is_api_mode())

    manager.configure(api_key='test-key-1234567890123456')

    print("After configure - _configured:", manager._configured)
    print("After configure - _logger:", manager._logger)
    print("Logger is_api_mode:", mock_logger_instance.is_api_mode())

    # Let's examine the mock calls
    print("Logger class calls:", mock_logger_class.call_count)
    if mock_logger_class.call_count > 0:
        print("Last call args:", mock_logger_class.call_args)