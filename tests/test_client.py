import pytest
from unittest.mock import Mock, patch, AsyncMock
import sys
import os
import httpx
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from baselog.api.client import APIClient
from baselog.api.config import APIConfig, Timeouts, RetryStrategy, Environment
from baselog.api.models import LogModel, APIResponse, LogResponse
from baselog.api.auth import AuthManager


class TestAPIClient:
    """Test cases for the APIClient class."""

    @pytest.fixture
    def mock_config(self):
        """Create a mock configuration for testing."""
        return APIConfig(
            base_url="https://api.test.com",
            api_key="test-api-key-that-is-at-least-16-characters-long",
            environment=Environment.DEVELOPMENT,
            timeouts=Timeouts(),
            retry_strategy=RetryStrategy()
        )

    @pytest.fixture
    def mock_auth_manager(self):
        """Create a mock auth manager for testing."""
        return AuthManager('test-api-key-that-is-at-least-16-characters-long')

    def test_client_initialization_with_config(self, mock_config):
        """Test APIClient initialization with provided config."""
        auth_manager = AuthManager('test-api-key-that-is-at-least-16-characters-long')
        client = APIClient(mock_config, auth_manager)

        assert client.config == mock_config
        assert client.config.base_url == "https://api.test.com"
        assert client.config.api_key == "test-api-key-that-is-at-least-16-characters-long"
        assert client.auth_manager == auth_manager

    def test_client_initialization_without_config(self):
        """Test APIClient initialization without config (creates default config)."""
        with patch('baselog.api.client.load_config') as mock_load_config:
            mock_config = APIConfig(
                base_url="https://env-config.com",
                api_key="test-api-key-that-is-at-least-16-characters-long",
                environment=Environment.PRODUCTION,
                timeouts=Timeouts(),
                retry_strategy=RetryStrategy()
            )
            mock_load_config.return_value = mock_config

            client = APIClient()

            assert client.config == mock_config
            assert client.auth_manager is not None
            mock_load_config.assert_called_once()

    @patch('baselog.api.client.httpx.AsyncClient')
    def test_setup_http_client(self, mock_async_client, mock_config, mock_auth_manager):
        """Test HTTP client setup with proper configuration."""
        mock_http_client = Mock()
        mock_async_client.return_value = mock_http_client

        client = APIClient(mock_config, mock_auth_manager)

        # Verify AsyncClient was called with correct parameters
        mock_async_client.assert_called_once()
        call_args = mock_async_client.call_args

        assert call_args.kwargs['base_url'] == "https://api.test.com"
        assert 'timeout' in call_args.kwargs
        assert 'limits' in call_args.kwargs
        assert call_args.kwargs.get('http1') is True

    @patch('baselog.api.client.tenacity.Retrying')
    def test_setup_retry_strategy(self, mock_retrying, mock_config, mock_auth_manager):
        """Test retry strategy setup."""
        mock_retry_instance = Mock()
        mock_retrying.return_value = mock_retry_instance

        client = APIClient(mock_config, mock_auth_manager)

        # Verify Retrying was called with exponential backoff
        mock_retrying.assert_called_once()
        call_args = mock_retrying.call_args

        assert 'wait' in call_args.kwargs
        assert call_args.kwargs['wait'].multiplier == mock_config.retry_strategy.backoff_factor

    def test_client_attributes(self, mock_config, mock_auth_manager):
        """Test that client has all required attributes."""
        with patch('baselog.api.client.httpx.AsyncClient'), \
             patch('baselog.api.client.tenacity.Retrying'):

            client = APIClient(mock_config, mock_auth_manager)

            # Test required attributes
            assert hasattr(client, 'config')
            assert hasattr(client, 'client')
            assert hasattr(client, 'retry_strategy')
            assert client.config is mock_config
            assert client.client is not None
            assert client.retry_strategy is not None

    @pytest.mark.asyncio
    async def test_send_log_successful(self, mock_config):
        """Test successful log sending."""
        with patch('baselog.api.client.httpx.AsyncClient') as mock_http_client, \
             patch('baselog.api.client.tenacity.Retrying') as mock_retrying:

            # Setup mocks
            mock_response = Mock()
            mock_response.json.return_value = {'id': 'log123', 'status': 'created'}
            mock_response.headers = {'X-Request-ID': 'req-123'}

            # Create async mock for post method
            mock_post = AsyncMock(return_value=mock_response)
            mock_http_client.return_value.post = mock_post
            mock_retrying.return_value = Mock()

            # Create client and auth manager
            auth_manager = AuthManager('test-api-key-that-is-at-least-16-characters-long')
            client = APIClient(mock_config, auth_manager)

            # Create test log
            log = LogModel(level='info', message='Test log message')

            # Call send_log
            response = await client.send_log(log)

            # Verify response
            assert response.success is True
            assert response.request_id == 'req-123'
            assert isinstance(response.data, LogResponse)
            assert response.data.success is True
            assert response.data.data == {'id': 'log123', 'status': 'created'}

            # Verify HTTP call was made correctly
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            assert call_args.kwargs['json']['message'] == 'Test log message'
            assert call_args.kwargs['headers']['Content-Type'] == 'application/json'

    @pytest.mark.asyncio
    async def test_send_log_with_correlation_id(self, mock_config):
        """Test log sending with existing correlation ID."""
        with patch('baselog.api.client.httpx.AsyncClient') as mock_http_client, \
             patch('baselog.api.client.tenacity.Retrying') as mock_retrying:

            # Setup mocks
            mock_response = Mock()
            mock_response.json.return_value = {'id': 'log123'}
            mock_response.headers = {'X-Request-ID': 'req-123'}

            # Create async mock for post method
            mock_post = AsyncMock(return_value=mock_response)
            mock_http_client.return_value.post = mock_post
            mock_retrying.return_value = Mock()

            auth_manager = AuthManager('test-api-key-that-is-at-least-16-characters-long')
            client = APIClient(mock_config, auth_manager)

            # Create log with correlation ID
            log = LogModel(level='error', message='Error message', correlation_id='corr-456')

            response = await client.send_log(log)

            # Verify correlation ID was preserved
            assert response.data.correlation_id == 'corr-456'

    @pytest.mark.asyncio
    async def test_send_log_authentication_error(self, mock_config):
        """Test authentication error handling (401, 403)."""
        with patch('baselog.api.client.httpx.AsyncClient') as mock_http_client, \
             patch('baselog.api.client.tenacity.Retrying') as mock_retrying:

            # Setup error response
            mock_response = Mock()
            mock_response.status_code = 401
            mock_http_client.return_value.post.side_effect = Mock()
            mock_http_client.return_value.post.side_effect = Mock()
            mock_http_client.return_value.post.side_effect.side_effect = mock_http_client.return_value.post.side_effect
            mock_http_client.return_value.post.side_effect.side_effect.side_effect = httpx.HTTPStatusError(
                'Unauthorized', request=Mock(), response=mock_response
            )
            mock_retrying.return_value = Mock()

            auth_manager = AuthManager('test-api-key-that-is-at-least-16-characters-long')
            client = APIClient(mock_config, auth_manager)

            log = LogModel(level='info', message='Test message')

            # Verify authentication error is raised
            from baselog.api.exceptions import APIAuthenticationError
            with pytest.raises(APIAuthenticationError) as exc_info:
                await client.send_log(log)

            assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_send_log_rate_limit_error(self, mock_config):
        """Test rate limiting error handling (429)."""
        with patch('baselog.api.client.httpx.AsyncClient') as mock_http_client, \
             patch('baselog.api.client.tenacity.Retrying') as mock_retrying:

            # Setup rate limiting response
            mock_response = Mock()
            mock_response.status_code = 429
            mock_response.headers = {'Retry-After': '30'}
            mock_http_client.return_value.post.side_effect = httpx.HTTPStatusError(
                'Too Many Requests', request=Mock(), response=mock_response
            )
            mock_retrying.return_value = Mock()

            auth_manager = AuthManager('test-api-key-that-is-at-least-16-characters-long')
            client = APIClient(mock_config, auth_manager)

            log = LogModel(level='info', message='Test message')

            # Verify API error with retry after is raised
            from baselog.api.exceptions import APIError
            with pytest.raises(APIError) as exc_info:
                await client.send_log(log)

            assert exc_info.value.status_code == 429
            assert exc_info.value.retry_after == 30

    @pytest.mark.asyncio
    async def test_send_log_timeout_error(self, mock_config):
        """Test timeout error handling."""
        with patch('baselog.api.client.httpx.AsyncClient') as mock_http_client, \
             patch('baselog.api.client.tenacity.Retrying') as mock_retrying:

            mock_http_client.return_value.post.side_effect = httpx.TimeoutException('Request timeout')
            mock_retrying.return_value = Mock()

            auth_manager = AuthManager('test-api-key-that-is-at-least-16-characters-long')
            client = APIClient(mock_config, auth_manager)

            log = LogModel(level='info', message='Test message')

            # Verify timeout error is raised
            from baselog.api.exceptions import APITimeoutError
            with pytest.raises(APITimeoutError) as exc_info:
                await client.send_log(log)

            assert 'timeout' in str(exc_info.value)

    def test_send_log_validation_error(self, mock_config):
        """Test input validation error."""
        auth_manager = AuthManager('test-api-key-that-is-at-least-16-characters-long')
        client = APIClient(mock_config, auth_manager)

        # Test with a valid message first
        valid_log = LogModel(level='info', message='valid message')
        assert valid_log.message == 'valid message'  # Should not raise error

        # Test what happens when message becomes empty after validation
        # This should not happen with normal LogModel usage, but we test the check
        log = LogModel(level='info', message='valid message')
        # Simulate message being cleared (edge case)
        log.message = ''

        with pytest.raises(ValueError) as exc_info:
            import asyncio
            asyncio.run(client.send_log(log))

        assert 'Message is required' in str(exc_info.value)

    def test_generate_correlation_id(self, mock_config):
        """Test correlation ID generation."""
        auth_manager = AuthManager('test-api-key-that-is-at-least-16-characters-long')
        client = APIClient(mock_config, auth_manager)

        correlation_id = client._generate_correlation_id()

        assert isinstance(correlation_id, str)
        assert len(correlation_id) == 36  # UUID length
        assert '-' in correlation_id  # UUID format

    def test_serialize_log_model(self, mock_config):
        """Test LogModel serialization."""
        auth_manager = AuthManager('test-api-key-that-is-at-least-16-characters-long')
        client = APIClient(mock_config, auth_manager)

        # Test basic serialization
        log = LogModel(level='info', message='test message')
        result = client._serialize_log_model(log)

        assert result['message'] == 'test message'
        assert result['level'] == 'info'
        assert 'category' not in result  # Should not be present when None
        assert 'tags' not in result  # Should not be present when empty

        # Test with category and tags
        log_with_data = LogModel(
            level='error',
            message='error message',
            category='auth',
            tags=['security', 'login']
        )
        result = client._serialize_log_model(log_with_data)

        assert result['category'] == 'auth'
        assert result['tags'] == ['security', 'login']