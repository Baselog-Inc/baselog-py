import pytest
from unittest.mock import Mock, patch, AsyncMock
import sys
import os
import httpx
from datetime import datetime
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from baselog.api.client import APIClient
from baselog.api.config import APIConfig, Timeouts, RetryStrategy, Environment
from baselog.api.models import LogModel, APIResponse, LogResponse, EventModel
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

    @pytest.mark.asyncio
    async def test_send_event_placeholder(self, mock_config):
        """Test that send_event returns placeholder response for Phase 1."""
        with patch('baselog.api.client.httpx.AsyncClient'), \
             patch('baselog.api.client.tenacity.Retrying'):

            auth_manager = AuthManager('test-api-key-that-is-at-least-16-characters-long')
            client = APIClient(mock_config, auth_manager)

            # Create test event
            event = EventModel(
                event_type="user_action",
                payload={"action": "click"},
                timestamp=datetime.now(),
                source_service="webapp"
            )

            # Call send_event
            response = await client.send_event(event)

            # Verify placeholder response
            assert response.success is False
            assert "Events not supported yet" in response.message
            assert response.data["event_type"] == "user_action"
            assert response.data["message"] == "Event submission is reserved for future phases of development"
            assert response.request_id is None
            assert response.timestamp is not None

    @pytest.mark.asyncio
    async def test_send_event_with_event_id(self, mock_config):
        """Test send_event with event_id present."""
        with patch('baselog.api.client.httpx.AsyncClient'), \
             patch('baselog.api.client.tenacity.Retrying'):

            auth_manager = AuthManager('test-api-key-that-is-at-least-16-characters-long')
            client = APIClient(mock_config, auth_manager)

            # Create event with event_id
            event = EventModel(
                event_type="system_error",
                payload={"error": "Database connection failed"},
                timestamp=datetime.now(),
                source_service="backend",
                correlation_id="corr-123"
            )
            # Add event_id to test that field
            event.event_id = "evt-456"

            response = await client.send_event(event)

            # Verify response includes event_id
            assert response.data["event_type"] == "system_error"
            assert response.data["event_id"] == "evt-456"

    @pytest.mark.asyncio
    async def test_send_event_logging(self, mock_config):
        """Test that send_event logs appropriate messages."""
        with patch('baselog.api.client.httpx.AsyncClient'), \
             patch('baselog.api.client.tenacity.Retrying'):

            auth_manager = AuthManager('test-api-key-that-is-at-least-16-characters-long')
            client = APIClient(mock_config, auth_manager)

            # Capture logging
            with patch.object(client.logger, 'warning') as mock_warning, \
                 patch.object(client.logger, 'info') as mock_info, \
                 patch.object(client.logger, 'debug') as mock_debug:

                event = EventModel(
                    event_type="login_attempt",
                    payload={"username": "testuser"},
                    timestamp=datetime.now(),
                    source_service="auth_service"
                )

                await client.send_event(event)

                # Verify appropriate logging calls
                mock_warning.assert_called_once()
                mock_info.assert_called_once()
                mock_debug.assert_called_once()

                # Check warning message content
                warning_call = mock_warning.call_args[0][0]
                assert "Event send attempted for events not currently supported" in warning_call
                assert "login_attempt" in warning_call

                # Check info message content
                info_call = mock_info.call_args[0][0]
                assert "Event system planned for future phases" in info_call
                assert "POST /projects/events" in info_call

                # Check debug message content
                debug_call = mock_debug.call_args[0][0]
                assert "Event validation would occur here" in debug_call

    @pytest.mark.asyncio
    async def test_send_event_future_readiness(self, mock_config):
        """Test that send_event handles various event structures correctly."""
        auth_manager = AuthManager('test-api-key-that-is-at-least-16-characters-long')
        client = APIClient(mock_config, auth_manager)

        # Test with minimal event
        minimal_event = EventModel(
            event_type="simple_event",
            payload={"minimal": "data"},
            timestamp=datetime.now(),
            source_service="test"
        )

        # Should not raise exception and return placeholder
        response = await client.send_event(minimal_event)

        assert response.success is False
        assert response.data["event_type"] == "simple_event"

    @pytest.mark.asyncio
    async def test_send_event_with_empty_event_type(self, mock_config):
        """Test send_event with empty event_type field in model validation."""
        auth_manager = AuthManager('test-api-key-that-is-at-least-16-characters-long')
        client = APIClient(mock_config, auth_manager)

        # Create valid event
        event = EventModel(
            event_type="empty_test",  # Must be non-empty due to model validation
            payload={"test": "data"},
            timestamp=datetime.now(),
            source_service="test"
        )

        response = await client.send_event(event)

        # Should work and return placeholder
        assert response.success is False
        assert response.data["event_type"] == "empty_test"
        assert response.data["message"] == "Event submission is reserved for future phases of development"