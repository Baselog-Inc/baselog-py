import asyncio
import concurrent.futures
import logging
from typing import Optional
from .api.client import APIClient
from .api.config import APIConfig
from .api.models import LogModel, APIResponse
from .api.exceptions import APIError, APIAuthenticationError, APITimeoutError


class SyncAPIClient:
    """
    Synchronous wrapper around async APIClient for user-facing sync interface.

    This class handles the async/sync bridge, allowing the logger to use
    synchronous methods while the underlying API client remains async.
    """

    def __init__(self, config: APIConfig):
        """
        Initialize SyncAPIClient with configuration.

        Args:
            config: APIConfig instance with API settings
        """
        self.config = config
        self._async_client: Optional[APIClient] = None
        self._event_loop: Optional[asyncio.AbstractEventLoop] = None
        self.logger = logging.getLogger(__name__)

        # Initialize the async client
        self._setup_async_client()

    def _setup_async_client(self):
        """Setup the underlying async APIClient."""
        try:
            self._async_client = APIClient(self.config)
            self.logger.debug("SyncAPIClient initialized with async APIClient")
        except Exception as e:
            self.logger.error(f"Failed to initialize async client: {e}")
            raise

    def send_log_sync(self, log_data: LogModel) -> APIResponse:
        """
        Synchronous wrapper for sending logs via the async API client.

        Args:
            log_data: LogModel instance containing log information

        Returns:
            APIResponse with confirmation of log creation

        Raises:
            APIError: For API-related errors
            APIAuthenticationError: For authentication failures
            APITimeoutError: For timeout-related errors
        """
        if self._async_client is None:
            raise APIError("Async client not initialized")

        return self._handle_sync_log_sending(log_data)

    def _handle_sync_log_sending(self, log_data: LogModel) -> APIResponse:
        """
        Handle log sending across different async contexts.

        This method intelligently handles different scenarios:
        1. No event loop running
        2. Event loop already running
        3. Event loop creation errors
        """
        try:
            # Try to get existing event loop
            loop = asyncio.get_event_loop()

            if loop.is_running():
                # We're in an async context - use thread pool
                return self._send_log_in_async_context(log_data, loop)
            else:
                # No running loop - can use asyncio.run
                return asyncio.run(self._async_client.send_log(log_data))
        except RuntimeError:
            # No event loop exists - create new one
            return asyncio.run(self._async_client.send_log(log_data))
        except Exception as e:
            self.logger.error(f"Failed to send log synchronously: {e}")
            raise

    def _send_log_in_async_context(self, log_data: LogModel, loop: asyncio.AbstractEventLoop) -> APIResponse:
        """
        Handle log sending when already in an async context.

        Args:
            log_data: LogModel instance
            loop: Current event loop

        Returns:
            APIResponse from the API call
        """
        import concurrent.futures

        # Use a thread pool to run the async operation
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(
                asyncio.run,
                self._async_client.send_log(log_data)
            )
            return future.result(timeout=30)  # 30 second timeout

    def close(self) -> None:
        """
        Cleanup resources and close the underlying async client.

        This method ensures proper cleanup of HTTP connections and resources.
        """
        if self._async_client:
            try:
                # Try to close in existing loop first
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # Use thread pool for cleanup
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(
                            asyncio.run,
                            self._async_client.close()
                        )
                        future.result(timeout=10)
                else:
                    asyncio.run(self._async_client.close())
            except Exception as e:
                self.logger.warning(f"Error closing async client: {e}")
            finally:
                self._async_client = None

        self.logger.debug("SyncAPIClient closed")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - cleanup resources."""
        self.close()

    @property
    def is_connected(self) -> bool:
        """Check if the sync client is properly connected."""
        return self._async_client is not None