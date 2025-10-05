import httpx
import tenacity
from typing import Optional, Dict, Any
from datetime import datetime

from .models import LogModel
from .config import APIConfig, Timeouts, RetryStrategy, load_config, Environment


class APIClient:
    """
    Main HTTP client for all communications with the baselog backend.

    Handles HTTP requests, authentication, connection pooling, timeout configuration,
    and retry logic for resilient API communications.
    """

    def __init__(self, config: Optional[APIConfig] = None):
        """
        Initialize the APIClient with configuration.

        Args:
            config: API configuration. If None, loads from environment.
        """
        self.config = config or load_config()

        # Setup HTTP client with connection pooling and timeout configuration
        self._setup_http_client()

        # Setup retry strategy
        self._setup_retry_strategy()

    def _setup_http_client(self):
        """Setup the underlying HTTP client with connection pooling and timeouts."""
        timeout_config = self.config.timeouts

        self.http_client = httpx.AsyncClient(
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