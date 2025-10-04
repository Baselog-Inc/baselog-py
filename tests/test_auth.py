"""Tests for authentication module."""

import pytest
from baselog.api.auth import (
    AuthManager,
    AuthenticationError,
    InvalidAPIKeyError,
    MissingAPIKeyError
)


class TestAuthManager:
    """Test cases for AuthManager class."""

    def test_create_auth_manager_with_valid_key(self):
        """Test creating AuthManager with valid API key."""
        api_key = "test_key_1234567890"
        auth_manager = AuthManager(api_key=api_key)

        assert auth_manager.api_key == api_key
        assert auth_manager.get_masked_api_key() == "test...7890"

    def test_from_config_factory_method(self):
        """Test factory method from_config."""
        api_key = "config_test_key_123456789"
        auth_manager = AuthManager.from_config(api_key)

        assert auth_manager.api_key == api_key
        assert auth_manager.get_masked_api_key() == "conf...6789"

    def test_validate_api_key_success(self):
        """Test successful API key validation."""
        api_key = "valid_api_key_1234567890"
        validated_key = AuthManager(api_key=api_key).validate_api_key(api_key)

        assert validated_key == api_key.strip()

    def test_validate_api_key_strip_whitespace(self):
        """Test API key validation strips whitespace."""
        api_key = "  valid_api_key_1234567890  "
        validated_key = AuthManager(api_key=api_key).validate_api_key(api_key)

        assert validated_key == "valid_api_key_1234567890"

    def test_validate_api_key_too_short(self):
        """Test validation fails for API key too short."""
        short_key = "short"

        with pytest.raises(InvalidAPIKeyError, match="at least 16 characters"):
            AuthManager(api_key=short_key).validate_api_key(short_key)

    def test_validate_api_key_empty_string(self):
        """Test validation fails for empty API key."""
        with pytest.raises(ValueError, match="non-empty string"):
            AuthManager(api_key="")

    def test_validate_api_key_none(self):
        """Test validation fails for None API key."""
        with pytest.raises(ValueError, match="non-empty string"):
            AuthManager(api_key=None).validate_api_key(None)

    def test_validate_api_key_invalid_characters(self):
        """Test validation fails for API key with invalid characters."""
        invalid_key = "invalid@key#12345678"  # Make it long enough

        # Create a valid auth manager first, then test validation
        valid_auth_manager = AuthManager(api_key="valid1234567890valid")
        with pytest.raises(InvalidAPIKeyError, match="invalid characters"):
            valid_auth_manager.validate_api_key(invalid_key)

    def test_validate_api_key_valid_special_chars(self):
        """Test validation passes for API key with valid special characters."""
        valid_key = "valid-api_key.123+456_789"
        validated_key = AuthManager(api_key=valid_key).validate_api_key(valid_key)

        assert validated_key == valid_key

    def test_get_auth_headers(self):
        """Test authentication headers generation."""
        api_key = "header_test_key_1234567890"
        auth_manager = AuthManager(api_key=api_key)
        headers = auth_manager.get_auth_headers()

        expected_headers = {
            'X-API-Key': api_key,
            'Content-Type': 'application/json',
            'User-Agent': 'baselog-python-client/1.0'
        }

        assert headers == expected_headers

    def test_get_masked_api_key(self):
        """Test API key masking."""
        api_key = "test_key_1234567890"
        auth_manager = AuthManager(api_key=api_key)
        masked_key = auth_manager.get_masked_api_key()

        assert masked_key == "test...7890"

    def test_mask_api_key_short_key(self):
        """Test masking for API keys that are barely long enough."""
        short_key = "short123456789012"  # 16 chars minimum
        auth_manager = AuthManager(api_key=short_key)
        masked_key = auth_manager.get_masked_api_key()

        assert masked_key == "shor...9012"

    def test_mask_api_key_minimum_length(self):
        """Test masking for API keys at minimum length."""
        minimal_key = "abcd1234efgh5678"  # 16 chars minimum
        auth_manager = AuthManager(api_key=minimal_key)
        masked_key = auth_manager.get_masked_api_key()

        assert masked_key == "abcd...5678"

    def test_post_initialization_validation(self):
        """Test that validation runs on initialization."""
        api_key = "post_valid_key_1234567890"
        auth_manager = AuthManager(api_key=api_key)

        assert auth_manager.api_key == api_key
        assert auth_manager._masked_key == "post...7890"

    def test_clean_string_in_validation(self):
        """Test that validation removes leading/trailing whitespace."""
        api_key = "  clean_key_1234567890  "
        auth_manager = AuthManager(api_key=api_key)

        assert auth_manager.api_key == "clean_key_1234567890"
        assert auth_manager.get_masked_api_key() == "clea...7890"


class TestAuthenticationErrors:
    """Test cases for authentication error classes."""

    def test_authentication_error_base(self):
        """Test base AuthenticationError."""
        with pytest.raises(AuthenticationError):
            raise AuthenticationError("Test message")

    def test_invalid_api_key_error(self):
        """Test InvalidAPIKeyError."""
        with pytest.raises(InvalidAPIKeyError):
            raise InvalidAPIKeyError("Invalid key format")

    def test_missing_api_key_error(self):
        """Test MissingAPIKeyError."""
        with pytest.raises(MissingAPIKeyError):
            raise MissingAPIKeyError("Missing key")

    def test_error_hierarchy(self):
        """Test error class hierarchy."""
        assert issubclass(InvalidAPIKeyError, AuthenticationError)
        assert issubclass(MissingAPIKeyError, AuthenticationError)
        assert not issubclass(InvalidAPIKeyError, MissingAPIKeyError)


class TestAuthManagerIntegration:
    """Integration tests for AuthManager."""

    def test_full_workflow(self):
        """Test complete authentication workflow."""
        api_key = "integration_test_key_1234567890"

        # Create auth manager
        auth_manager = AuthManager.from_config(api_key)

        # Test validation
        validated_key = auth_manager.validate_api_key(api_key)
        assert validated_key == api_key

        # Test headers
        headers = auth_manager.get_auth_headers()
        assert headers['X-API-Key'] == api_key
        assert headers['Content-Type'] == 'application/json'
        assert headers['User-Agent'] == 'baselog-python-client/1.0'

        # Test masking
        masked_key = auth_manager.get_masked_api_key()
        assert masked_key == "inte...7890"
        assert api_key not in masked_key

    def test_long_api_key_masking(self):
        """Test masking works correctly for long API keys."""
        long_key = "a" * 32
        auth_manager = AuthManager(api_key=long_key)
        masked_key = auth_manager.get_masked_api_key()

        assert masked_key == "aaaa...aaaa"
        assert len(masked_key) == 11  # 4 + 3 dots + 4
        assert masked_key != long_key

    def test_edge_case_characters(self):
        """Test API key with edge case valid characters."""
        edge_key = "test-api.key_123+456.789"
        auth_manager = AuthManager(api_key=edge_key)

        assert auth_manager.api_key == edge_key
        assert auth_manager.get_masked_api_key() == "test....789"