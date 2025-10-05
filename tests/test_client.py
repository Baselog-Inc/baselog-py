import pytest
from unittest.mock import Mock, patch
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from baselog.api.client import APIClient
from baselog.api.config import APIConfig, Timeouts, RetryStrategy, Environment


class TestAPIClient:
    """Test cases for the APIClient class."""

    @pytest.fixture
    def mock_config(self):
        """Create a mock configuration for testing."""
        return APIConfig(
            base_url="https://api.test.com",
            api_key="test-api-key",
            environment=Environment.DEVELOPMENT,
            timeouts=Timeouts(),
            retry_strategy=RetryStrategy()
        )

    def test_client_initialization_with_config(self, mock_config):
        """Test APIClient initialization with provided config."""
        client = APIClient(mock_config)

        assert client.config == mock_config
        assert client.config.base_url == "https://api.test.com"
        assert client.config.api_key == "test-api-key"

    def test_client_initialization_without_config(self):
        """Test APIClient initialization without config (creates default config)."""
        with patch('baselog.api.client.load_config') as mock_load_config:
            mock_config = APIConfig(
                base_url="https://env-config.com",
                api_key="env-key",
                environment=Environment.PRODUCTION,
                timeouts=Timeouts(),
                retry_strategy=RetryStrategy()
            )
            mock_load_config.return_value = mock_config

            client = APIClient()

            assert client.config == mock_config
            mock_load_config.assert_called_once()

    @patch('baselog.api.client.httpx.AsyncClient')
    def test_setup_http_client(self, mock_async_client, mock_config):
        """Test HTTP client setup with proper configuration."""
        mock_http_client = Mock()
        mock_async_client.return_value = mock_http_client

        client = APIClient(mock_config)

        # Verify AsyncClient was called with correct parameters
        mock_async_client.assert_called_once()
        call_args = mock_async_client.call_args

        assert call_args.kwargs['base_url'] == "https://api.test.com"
        assert 'timeout' in call_args.kwargs
        assert 'limits' in call_args.kwargs
        assert call_args.kwargs.get('http1') is True

    @patch('baselog.api.client.tenacity.Retrying')
    def test_setup_retry_strategy(self, mock_retrying, mock_config):
        """Test retry strategy setup."""
        mock_retry_instance = Mock()
        mock_retrying.return_value = mock_retry_instance

        client = APIClient(mock_config)

        # Verify Retrying was called with exponential backoff
        mock_retrying.assert_called_once()
        call_args = mock_retrying.call_args

        assert 'wait' in call_args.kwargs
        assert call_args.kwargs['wait'].multiplier == mock_config.retry_strategy.backoff_factor

    def test_client_attributes(self, mock_config):
        """Test that client has all required attributes."""
        with patch('baselog.api.client.httpx.AsyncClient'), \
             patch('baselog.api.client.tenacity.Retrying'):

            client = APIClient(mock_config)

            # Test required attributes
            assert hasattr(client, 'config')
            assert hasattr(client, 'http_client')
            assert hasattr(client, 'retry_strategy')
            assert client.config is mock_config
            assert client.http_client is not None
            assert client.retry_strategy is not None