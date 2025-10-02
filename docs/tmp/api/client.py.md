# client.py - Principal HTTP Client

## Role
The core of the HTTP client, responsible for all network communications to the baselog backend.

## Responsibilities
- Managing HTTP requests to baselog endpoints
- Configuring timeouts (30s default)
- Managing retry logic with exponential backoff
- Implementing connection pooling
- Validating responses and HTTP codes
- Managing authentication headers
- Handling network and API errors

## Key Methods

### Implementation Details
Each method uses the shared `httpx.AsyncClient` for requests, inheriting configuration from `config.py` (timeouts, retries via tenacity decorators). Errors are raised as custom `APIError` or subclasses. Always async for non-blocking I/O.

```python
class APIClient:
    def __init__(self, config):
        self.config = config
        self.auth_headers = AuthManager(config.api_key).get_auth_headers()  # Static for Phase 1
        limits = httpx.Limits(
            max_keepalive_connections=config.pool_size,  # From config
            max_connections=config.max_connections
        )
        timeout_config = httpx.Timeout(**config.timeouts.to_dict())
        self.client = httpx.AsyncClient(
            base_url=config.base_url,
            limits=limits,
            timeout=timeout_config,
            headers=self.auth_headers
        )

    async def send_log(self, log_data: LogModel) -> APIResponse:  # POST /projects/logs
    async def send_event(self, event_data: EventModel) -> APIResponse:  # Reserved for future
    async def health_check(self) -> bool:  # Optional /health endpoint
    async def close(self):
```

#### `async def send_log(log_data: LogModel) -> APIResponse`
**Purpose:** Sends a single log entry to the backend via POST `/projects/logs`, confirming creation.

**Step-by-Step Implementation:**
1. **Input Validation:** Check required fields (e.g., `if not log_data.message: raise ValueError("Message required")`). Serialize to dict: `json_data = log_data.dict(exclude_unset=True)` to exclude unset optionals.
2. **URL Construction:** `url = f"{self.config.base_url}/projects/logs"`.
3. **Retry Decorator:** Wrap with `@retry` from tenacity, using `self.config.retry_strategy` (max_attempts=3, backoff, status_forcelist=[429, 500-504]).
4. **Request Execution:**
   ```python
   @retry(...)
   async def _send(self, json_data):
       response = await self.client.post(
           url,
           json=json_data,
           headers={**self.auth_headers, 'Content-Type': 'application/json'},
           timeout=self.config.timeouts.read  # Specific timeout if needed
       )
       response.raise_for_status()  # Raise if not 2xx
       return response
   ```
5. **Response Handling:** Parse JSON: `data = response.json()`. Return `APIResponse(success=True, data=LogResponse(data), request_id=response.headers.get('X-Request-ID'))`. Add `timestamp`.
6. **Error Handling:** Catch `httpx.HTTPStatusError` → map to `APIError` or subclass (e.g., 401 → `APIAuthenticationError`). `httpx.TimeoutException` → `APITimeoutError`. Reraise custom exceptions.
7. **Logging:** `logger.info(f"Log sent with correlation_id {log_data.correlation_id}")` (without sensitive data).

**Notes:** Single log only (batching in Phase 2). Performance: ~50ms avg. Test with mock response.

#### `async def send_event(event_data: EventModel) -> APIResponse`
**Purpose:** Reserved for future event submission (not implemented in backend yet).

**Step-by-Step Implementation:**
1. **Input Validation:** Raise `NotImplementedError("Event system not available in Phase 1")` or optional stub: validate `event_data.event_type` non-empty.
2. **Stub Response:** Return `APIResponse(success=False, message="Events not supported yet")` to avoid breaking callers.
3. **Future Extension Plan:** Once backend ready, similar to `send_log` but POST to `/projects/events` (assumed). Use event_data.payload as json_data; add retry.
4. **Error Handling:** `APIError` for future network issues.
5. **Logging:** Warn "Event send attempted but skipped".

**Notes:** Placeholder; evolve to full async POST in later phases. No request in Phase 1 to save resources.

#### `async def health_check(self) -> bool`
**Purpose:** Quick check if the API is reachable (optional; not specified in backend, but useful for circuit breaker).

**Step-by-Step Implementation:**
1. **URL Construction:** `url = f"{self.config.base_url}/health"` (assumed endpoint; fallback to `/projects/logs` GET if no health).
2. **Request Execution:** Simple async GET with short timeout (5s):
   ```python
   async def _health_send(self):
       response = await self.client.get(url, timeout=5.0)
       response.raise_for_status()
       return response.status_code == 200
   ```
3. **Retry:** Minimal (1 attempt) or none; fast-fail for health.
4. **Response Handling:** Return `True` on 2xx; `False` otherwise (no APIResponse, just bool).
5. **Error Handling:** Swallow `httpx.ConnectError` → return `False`; no raises to keep it lightweight.
6. **Caching:** Optional: Cache result for 30s to avoid spam (via self._health_cache).

**Notes:** Used in circuit breaker (Phase 3); default to True if no endpoint. Test: Mock 200 for healthy, 503 for down.

#### `async def close(self)`
**Purpose:** Clean shutdown of httpx client and resources.

**Step-by-Step Implementation:**
1. **Resource Release:** `await self.client.aclose()` to close connections/pool.
2. **Cleanup:** Clear any caches (e.g., health check cache); optional: log "APIClient closed".
3. **Error Handling:** Swallow if already closed (idempotent).
4. **Usage:** Call in app shutdown (e.g., `await logger.close()`); context manager support:
   ```python
   async with APIClient(config) as client:
       await client.send_log(...)
   # Auto-closes
   ```

**Notes:** Prevents resource leaks; sync version calls `self.async_client.close()`. Always await in async code.

This expanded plan ensures the client is robust, configurable, and maintainable for Phase 1, with clear extension paths.