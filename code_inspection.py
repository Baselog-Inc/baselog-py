import sys
sys.path.insert(0, 'src')

# Simple test without mocks
from baselog.logger_manager import LoggerManager

# Create a manager and inspect the actual code execution
manager = LoggerManager()

print("=== Real Logger Test ===")
print("Before configure - _configured:", manager._configured)
print("Before configure - _logger:", manager._logger)

# Try to configure with a real API key that should fail
try:
    manager.configure(api_key="invalid-key")
    print("After configure - _configured:", manager._configured)
    print("After configure - _logger:", manager._logger)
    if manager._logger:
        print("Logger mode:", manager._logger.mode)
        print("Logger is_api_mode():", manager._logger.is_api_mode())
except Exception as e:
    print("Exception during configure:", e)

# Now try reset
manager.reset()
print("After reset - _configured:", manager._configured)
print("After reset - _logger:", manager._logger)