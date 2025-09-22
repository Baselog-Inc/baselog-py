import pytest
from loggy import info


def test_info_function():
    """Test calling the info function from loggy module"""
    # This test verifies the info function can be called without errors
    info("Test message")