# Sync Client Support for baselog API (sync-client.py.md)

## Overview
This document outlines the synchronous support for the baselog API client, providing a non-blocking alternative to the primary async client. It leverages httpx's sync capabilities while delegating to the async core for code reuse. This enables usage in synchronous contexts (e.g., scripts, Flask apps) without requiring event loops, while maintaining the performance benefits of async under the hood.

- **Goal:** Backward compatibility and flexibility; sync is a wrapper around async for simplicity.
- **Dependencies:** httpx (sync client), asyncio (for wrapping), concurrent.futures (ThreadPoolExecutor).
- **Key Principle:** No duplication, the sync client instantiates and wraps the async APIClient.

## Role
Provides synchronous versions of API methods (e.g., `send_log`) for environments without async support. Handles conversion from async to sync using `asyncio.run` or an executor to avoid blocking the main thread.

## Responsibilities
- Instantiating the underlying async `APIClient` and wrapping its methods in sync calls.
- Managing the event loop lifecycle safely (create/close per call or shared).
- Delegating configuration (timeouts, retries) from the core async client.
- Handling exceptions consistently (e.g., APIError remains the same).
- Ensuring resource cleanup (e.g., close executor on shutdown).

## Implementation Outline

### SyncAPIClient Class (Wrapper)
A thin wrapper around `APIClient` that runs async methods synchronously.

```python
import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Optional
from .client import APIClient  # Import async core
from .models import LogModel, APIResponse, EventModel

class SyncAPIClient:
    def __init__(self, config):
        self.async_client = APIClient(config)  # Delegates to async core
        self.executor = ThreadPoolExecutor(max_workers=1)  # For safe async-in-sync

    def send_log(self, log_data: LogModel) -> APIResponse:
        """Synchronous send_log wrapper."""
        # Run async method in controlled event loop
        loop = asyncio.new_event_loop()
        try:
            future = asyncio.ensure_future(self.async_client.send_log(log_data), loop=loop)
            return loop.run_until_complete(future)
        finally:
            loop.close()

    def send_event(self, event_data: EventModel) -> APIResponse:
        """Synchronous send_event (reserved; calls async version)."""
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(self.async_client.send_event(event_data))
        finally:
            loop.close()

    def health_check(self) -> bool:
        """Synchronous health check."""
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(self.async_client.health_check())
        finally:
            loop.close()

    def close(self):
        """Cleanup resources."""
        self.async_client.close()
        self.executor.shutdown(wait=True)
```

### Alternative: Using ThreadPoolExecutor for Non-Blocking
For better performance in multi-threaded sync contexts, run async in a separate thread.

```python
from concurrent.futures import ThreadPoolExecutor, as_completed

class ThreadedSyncAPIClient:
    def __init__(self, config):
        self.async_client = APIClient(config)
        self.executor = ThreadPoolExecutor(max_workers=4)  # Multiple for concurrent calls

    def send_log(self, log_data: LogModel) -> APIResponse:
        future = self.executor.submit(self._run_async_log, log_data)
        return future.result()  # Blocks until done

    async def _run_async_log(self, log_data: LogModel) -> APIResponse:
        await self.async_client.send_log(log_data)

    def close(self):
        self.async_client.close()
        self.executor.shutdown(wait=True)
```

## Integration with Logger
Extend the Logger to support sync mode via constructor flag.

```python
class Logger:
    def __init__(self, async_mode: bool = True, config=None):
        self.async_mode = async_mode
        self.client = APIClient(config) if async_mode else SyncAPIClient(config)

    # Async methods (always available)
    async def info(self, message: str, category: Optional[str] = None, tags: List[str] = []):
        log_data = LogModel(level="info", message=message, category=category, tags=tags)
        return await self.client.send_log(log_data)

    # Sync convenience methods
    def info_sync(self, message: str, category: Optional[str] = None, tags: List[str] = []):
        log_data = LogModel(level="info", message=message, category=category, tags=tags)
        if self.async_mode:
            return asyncio.run(self.info(message, category, tags))  # Simple run for async mode
        else:
            return self.client.send_log(log_data)  # Direct sync

    async def close(self):
        await self.client.close() if self.async_mode else self.client.close()
```

- **Usage Examples:**
  - Async: `await logger.info("Hello")` (in async context).
  - Sync: `logger.info_sync("Hello")` or `asyncio.run(logger.info("Hello"))`.

## Configuration Integration
- Inherits fully from `config.py` (Section 1.1): `SyncAPIClient(config)` uses the same `timeouts.to_dict()`, `retry_strategy`, `base_url`, etc.
- No additional env vars needed; sync mode just changes the client instantiation.

## Benefits and Trade-offs
### Benefits
- **Flexibility:** Use sync in non-async apps (e.g., Django views, scripts) without refactoring.
- **Code Reuse:** 90% shared with async; easy maintenance.
- **Performance:** Async core ensures efficiency; sync wrapper adds minimal overhead (~10ms per call via loop spawn).
- **Consistency:** Same error types (APIError), models (LogModel), and fallback logic.

### Trade-offs
- **Overhead:** Sync wrappers create temporary event loops (negligible for logging; avoid for high-frequency calls).
- **Debugging:** Sync errors surfacing from async may need tracebacks unwrapping.
- **Thread Safety:** Use ThreadPoolExecutor for multi-threaded sync to prevent loop conflicts.
- **Recommendation:** Prefer async mode in new code; sync for legacy/simplicity.

## Testing Sync Support
- **Unit Tests:** Mock async client; test `send_log` blocks and returns APIResponse.
- **Integration:** Run sync tests against mock server (e.g., `httpx` mock transport in sync mode).
- **Edge Cases:** Timeout propagation, retry behavior in sync, close() cleanup.

This design ensures the SDK is versatile for both async and sync environments, aligning with Phase 1's focus on robust API integration.