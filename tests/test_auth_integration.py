"""Integration tests for authentication module with configuration."""

import pytest
from unittest.mock import patch
from baselog.api.config import APIConfig, Environment, Timeouts, RetryStrategy
from baselog.api.auth import AuthManager, InvalidAPIKeyError


class TestAuthManagerAPIConfigIntegration:
    """Integration tests between AuthManager and APIConfig."""

    def test_create_auth_manager_from_config(self):
        """Test creating AuthManager from APIConfig."""
        config = APIConfig(
            base_url="https://baselog-api.vercel.app",
            api_key="config_integration_key_1234567890",
            environment=Environment.DEVELOPMENT,
            timeouts=Timeouts(),
            retry_strategy=RetryStrategy()
        )

        auth_manager = config.create_auth_manager()

        assert isinstance(auth_manager, AuthManager)
        assert auth_manager.api_key == "config_integration_key_1234567890"
        assert auth_manager.get_masked_api_key() == "conf...7890"

    def test_real_workflow_complete_integration(self):
        """Test complete real-world workflow integration."""
        # Create configuration
        config = APIConfig(
            base_url="https://baselog-api.vercel.app",
            api_key="real_workflow_key_1234567890",
            environment=Environment.PRODUCTION,
            timeouts=Timeouts(connect=5.0, read=10.0, write=10.0, pool=30.0),
            retry_strategy=RetryStrategy(max_attempts=5, backoff_factor=2.0),
            batch_size=50,
            batch_interval=2
        )

        # Create auth manager from config
        auth_manager = config.create_auth_manager()

        # Test that the API key is properly validated and masked
        assert auth_manager.api_key == "real_workflow_key_1234567890"
        assert auth_manager.get_masked_api_key() == "real...7890"

        # Test that headers are correctly generated
        headers = auth_manager.get_auth_headers()
        assert headers['X-API-Key'] == "real_workflow_key_1234567890"
        assert headers['Content-Type'] == 'application/json'
        assert headers['User-Agent'] == 'baselog-python-client/1.0'

        # Verify that masked key never exposes the real key
        assert config.api_key not in auth_manager.get_masked_api_key()

    def test_config_error_propagation(self):
        """Test that configuration errors properly propagate through auth manager."""
        config = APIConfig(
            base_url="https://baselog-api.vercel.app",
            api_key="short",  # This will cause validation error
            environment=Environment.DEVELOPMENT,
            timeouts=Timeouts(),
            retry_strategy=RetryStrategy()
        )

        # Should fail when auth manager is created
        with pytest.raises(InvalidAPIKeyError, match="at least 16 characters"):
            config.create_auth_manager()

    def test_multiple_environments_integration(self):
        """Test auth manager integration across different environments."""
        test_cases = [
            (Environment.DEVELOPMENT, "dev_key_1234567890"),
            (Environment.STAGING, "staging_key_1234567890"),
            (Environment.PRODUCTION, "prod_key_1234567890")
        ]

        for environment, api_key in test_cases:
            config = APIConfig(
                base_url="https://baselog-api.vercel.app",
                api_key=api_key,
                environment=environment,
                timeouts=Timeouts(),
                retry_strategy=RetryStrategy()
            )

            auth_manager = config.create_auth_manager()
            assert auth_manager.api_key == api_key

            # Check specific masking for each environment
            if "dev" in api_key:
                assert auth_manager.get_masked_api_key() == "devk...7890"
            elif "staging" in api_key:
                assert auth_manager.get_masked_api_key() == "stag...7890"
            elif "prod" in api_key:
                assert auth_manager.get_masked_api_key() == "prod...7890"

    def test_timeout_and_retry_combination(self):
        """Test auth manager with custom timeouts and retry strategies."""
        config = APIConfig(
            base_url="https://baselog-api.vercel.app",
            api_key="timeout_test_key_1234567890",
            environment=Environment.STAGING,
            timeouts=Timeouts(connect=2.0, read=5.0, write=5.0, pool=10.0),
            retry_strategy=RetryStrategy(
                max_attempts=3,
                backoff_factor=1.5,
                status_forcelist=[429, 500],
                allowed_methods=['POST']
            )
        )

        auth_manager = config.create_auth_manager()

        # Verify auth manager works with complex configuration
        assert auth_manager.api_key == "timeout_test_key_1234567890"
        assert auth_manager.get_masked_api_key() == "time...7890"

        # Headers should still be properly formatted
        headers = auth_manager.get_auth_headers()
        assert headers['X-API-Key'] == "timeout_test_key_1234567890"

    def test_batch_configuration_integration(self):
        """Test integration with batch configuration settings."""
        config = APIConfig(
            base_url="https://baselog-api.vercel.app",
            api_key="batch_test_key_1234567890",
            environment=Environment.DEVELOPMENT,
            timeouts=Timeouts(),
            retry_strategy=RetryStrategy(),
            batch_size=200,
            batch_interval=10
        )

        auth_manager = config.create_auth_manager()

        # Ensure batch settings don't affect auth manager
        assert auth_manager.api_key == "batch_test_key_1234567890"
        assert auth_manager.get_masked_api_key() == "batc...7890"

        # Auth manager should work independently of batch settings
        headers = auth_manager.get_auth_headers()
        assert headers['X-API-Key'] == "batch_test_key_1234567890"

    def test_context_manager_usage(self):
        """Test auth manager usage in context manager pattern."""
        config = APIConfig(
            base_url="https://baselog-api.vercel.app",
            api_key="context_test_key_1234567890",
            environment=Environment.PRODUCTION,
            timeouts=Timeouts(),
            retry_strategy=RetryStrategy()
        )

        # Test that auth manager can be used in typical patterns
        auth_manager = config.create_auth_manager()

        # Test 1: Key validation
        validated_key = auth_manager.validate_api_key("context_test_key_1234567890")
        assert validated_key == "context_test_key_1234567890"

        # Test 2: Secure logging
        masked_key = auth_manager.get_masked_api_key()
        assert masked_key == "cont...7890"
        assert "context_test_key_1234567890" not in masked_key

        # Test 3: Headers for API calls
        headers = auth_manager.get_auth_headers()
        required_headers = ['X-API-Key', 'Content-Type', 'User-Agent']
        for header in required_headers:
            assert header in headers

    def test_error_scenarios_integration(self):
        """Test various error scenarios in integration."""
        # Test with whitespace in API key
        config1 = APIConfig(
            base_url="https://baselog-api.vercel.app",
            api_key="  whitespace_test_key_1234567890  ",
            environment=Environment.DEVELOPMENT,
            timeouts=Timeouts(),
            retry_strategy=RetryStrategy()
        )

        auth_manager1 = config1.create_auth_manager()
        assert auth_manager1.api_key == "whitespace_test_key_1234567890"
        assert auth_manager1.get_masked_api_key() == "whit...7890"

        # Test with valid special characters
        config2 = APIConfig(
            base_url="https://baselog-api.vercel.app",
            api_key="special-chars_test.key_123+456",
            environment=Environment.DEVELOPMENT,
            timeouts=Timeouts(),
            retry_strategy=RetryStrategy()
        )

        auth_manager2 = config2.create_auth_manager()
        assert auth_manager2.api_key == "special-chars_test.key_123+456"
        assert auth_manager2.get_masked_api_key() == "spec...+456"