import logging
import json
from typing import Dict, Any, Optional
from datetime import datetime, timezone
import httpx
import tenacity

from .models import LogModel, APIResponse, LogResponse, EventModel
from .auth import AuthManager
from .config import APIConfig, Timeouts, RetryStrategy, load_config, Environment
from .exceptions import APIError, APIAuthenticationError, APITimeoutError


class APIClient:
    """
    Main HTTP client for all communications with the baselog backend.

    Handles HTTP requests, authentication, connection pooling, timeout configuration,
    and retry logic for resilient API communications.
    """

    # Retry configuration for all API calls
    _retry_config = {
        'wait': tenacity.wait_exponential(multiplier=1, min=4, max=10),
        'stop': tenacity.stop_after_attempt(3),
        'retry': tenacity.retry_if_exception_type((
            httpx.TimeoutException,
            httpx.ConnectError,
            httpx.RequestError,
        )),
        'before_sleep': tenacity.before_sleep_log(logging.getLogger(__name__), logging.INFO),
        'reraise': True
    }

    def __init__(self, config: Optional[APIConfig] = None, auth_manager: Optional[AuthManager] = None):
        """
        Initialize the APIClient with configuration and authentication.

        Args:
            config: API configuration. If None, loads from environment.
            auth_manager: AuthManager for authentication. If None, creates from config.
        """
        self.config = config or load_config()
        self.auth_manager = auth_manager or self.config.create_auth_manager()
        self.logger = logging.getLogger(__name__)

        # Setup HTTP client with connection pooling and timeout configuration
        self._setup_http_client()

        # Setup retry strategy
        self._setup_retry_strategy()

    def _setup_http_client(self):
        """Setup the underlying HTTP client with connection pooling and timeouts."""
        timeout_config = self.config.timeouts

        self.client = httpx.AsyncClient(
            base_url=self.config.base_url,
            timeout=httpx.Timeout(
                connect=timeout_config.connect,
                read=timeout_config.read,
                write=timeout_config.write,
                pool=timeout_config.pool
            ),
            limits=httpx.Limits(
                max_keepalive_connections=20,
                max_connections=100
            ),
            http1=True
        )

    def _setup_retry_strategy(self):
        """Setup retry strategy using tenacity."""
        retry_config = self.config.retry_strategy

        self.retry_strategy = tenacity.Retrying(
            wait=tenacity.wait_exponential(
                multiplier=retry_config.backoff_factor,
                min=1.0,
                max=60.0
            ),
            stop=tenacity.stop_after_attempt(retry_config.max_attempts),
            retry=tenacity.retry_if_exception_type((
                httpx.TimeoutException,
                httpx.NetworkError,
                httpx.ConnectError
            )),
            reraise=True
        )

    async def send_log(self, log_data: LogModel) -> APIResponse:
        """
        Send a single log entry to the backend via POST /projects/logs.

        Args:
            log_data: LogModel instance containing log information

        Returns:
            APIResponse with confirmation of log creation

        Raises:
            APIError: For API-related errors
            APIAuthenticationError: For authentication failures (401, 403)
            APITimeoutError: For timeout-related errors
            ValueError: For invalid input validation
        """
        # 1. Input Validation
        if not log_data.message:
            raise ValueError("Message is required for LogModel")

        if not hasattr(log_data, 'correlation_id') or not log_data.correlation_id:
            log_data.correlation_id = self._generate_correlation_id()

        # Serialize to dict, excluding unset optionals
        json_data = self._serialize_log_model(log_data)

        # 2. URL Construction
        url = f"{self.config.base_url}/projects/logs"

        # 3. Execute with retry logic
        try:
            response = await self._send_with_retry(url, json_data)

            # 4. Response Handling
            response_data = response.json()
            request_id = response.headers.get('X-Request-ID')

            # Convert to LogResponse if needed
            log_response = LogResponse(
                success=True,
                message="Log created successfully",
                data=response_data,
                request_id=request_id,
                timestamp=datetime.now(timezone.utc).isoformat(),
                correlation_id=log_data.correlation_id
            )

            self.logger.info(
                f"Log sent with correlation_id {log_data.correlation_id} "
                f"request_id {request_id}"
            )

            return APIResponse(
                success=True,
                data=log_response,
                request_id=request_id,
                timestamp=datetime.now(timezone.utc).isoformat()
            )

        except httpx.HTTPStatusError as e:
            # Map HTTP errors to custom exceptions
            if e.response.status_code in (401, 403):
                raise APIAuthenticationError(
                    f"Authentication failed: {e.response.status_code}",
                    status_code=e.response.status_code
                )
            elif e.response.status_code == 429:
                retry_after = int(e.response.headers.get('Retry-After', 60))
                raise APIError(
                    f"Rate limited: {e.response.status_code}",
                    status_code=e.response.status_code,
                    retry_after=retry_after
                )
            else:
                raise APIError(
                    f"API request failed: {e.response.status_code}",
                    status_code=e.response.status_code
                )

        except httpx.TimeoutException as e:
            raise APITimeoutError(
                f"Request timeout: {str(e)}",
                timeout_type="request"
            )

        except httpx.RequestError as e:
            raise APIError(
                f"Request error: {str(e)}",
                original_error=e
            )

    def _serialize_log_model(self, log_data: LogModel) -> Dict[str, Any]:
        """Serialize LogModel to dict excluding unset optionals."""
        if hasattr(log_data, 'model_dump'):
            return log_data.model_dump(exclude_unset=True)
        elif hasattr(log_data, 'dict'):
            return log_data.dict(exclude_unset=True)
        else:
            # Fallback manual serialization
            result = {
                'level': log_data.level.value if hasattr(log_data.level, 'value') else log_data.level,
                'message': log_data.message,
            }
            if log_data.category is not None:
                result['category'] = log_data.category
            if log_data.tags:
                result['tags'] = log_data.tags
            return result

    @tenacity.retry(**_retry_config)
    async def _send_with_retry(self, url: str, json_data: Dict[str, Any]) -> httpx.Response:
        """
        Internal method to send request with retry logic.

        Args:
            url: Target URL for the request
            json_data: JSON data to send in the request body

        Returns:
            httpx.Response: The HTTP response

        Raises:
            httpx.HTTPStatusError: For HTTP error responses
            httpx.TimeoutException: For timeout errors
            httpx.RequestError: For other request errors
        """
        # Get current auth headers
        current_headers = self.auth_manager.get_auth_headers()
        request_headers = {
            **current_headers,
            'Content-Type': 'application/json'
        }

        timeout = getattr(self.config.timeouts, 'read', 30.0)
        response = await self.client.post(
            url,
            json=json_data,
            headers=request_headers,
            timeout=timeout
        )

        response.raise_for_status()
        return response

    def _generate_correlation_id(self) -> str:
        """Generate a unique correlation ID for the log entry."""
        import uuid
        return str(uuid.uuid4())

    async def send_event(self, event_data: EventModel) -> APIResponse:
        """
        Placeholder for future event submission (not implemented in backend yet).

        Args:
            event_data: EventModel instance containing event information

        Returns:
            APIResponse indicating events are not supported yet

        Raises:
            NotImplementedError: Events are not implemented in Phase 1
            APIError: For future network issues when implemented
        """
        # Log the attempt for visibility
        event_type = getattr(event_data, 'event_type', 'unknown')
        self.logger.warning(
            f"Event send attempted for events not currently supported. "
            f"Event type: {event_type}. This functionality will be implemented in future phases."
        )

        # Provide helpful guidance for future implementation
        self.logger.info(
            "Event system planned for future phases. "
            "API endpoint expected: POST /projects/events"
        )

        # Basic input validation for future readiness
        if hasattr(event_data, 'event_type') and event_data.event_type:
            self.logger.debug(
                "Event validation would occur here for event_type: %s",
                event_data.event_type
            )

        # Return immediate response to avoid blocking callers
        return APIResponse(
            success=False,
            message="Events not supported yet - Phase 1 implementation",
            data={
                "event_type": getattr(event_data, 'event_type', None),
                "event_id": getattr(event_data, 'event_id', None),
                "message": "Event submission is reserved for future phases of development"
            },
            request_id=None,
            timestamp=datetime.now(timezone.utc).isoformat()
        )

    # === Future Extension Plan ===
    # When backend is ready for event submission, implement:
    #
    # @tenacity.retry(**self._retry_config)
    # async def send_event(self, event_data: EventModel) -> APIResponse:
    #     """Full implementation for future event submission."""
    #     url = f"{self.config.base_url}/projects/events"
    #     json_data = event_data.model_dump(exclude_unset=True)
    #
    #     response = await self._send_with_retry(url, json_data)
    #     data = response.json()
    #
    #     return APIResponse(
    #         success=True,
    #         data=data,
    #         request_id=response.headers.get('X-Request-ID'),
    #         timestamp=datetime.now(timezone.utc).isoformat()
    #     )
    #
    # This mirrors the send_log implementation but for /projects/events endpoint