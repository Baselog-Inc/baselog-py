# config.py - Configuration Management

## Role
Centralizes all dynamic API configuration, providing validated and environment-specific settings to other modules like the HTTP client (`client.py`). Acts as a single source of truth to avoid scattered environment variable access and ensure consistency.

## Responsibilities
- Loading configuration from environment variables (with support for .env files in development).
- Validating required parameters (e.g., API key, base URL) at startup.
- Managing environment-specific configurations (dev/staging/prod).
- Providing structured configuration objects (dataclasses) to other modules for type safety.
- Handling defaults and overrides (env vars take precedence over defaults).
- Early error detection for missing or invalid configurations.

## Key Methods and Classes

### Primary Function: `load_config()`
Loads and validates the full configuration, returning a `APIConfig` object.

```python
from typing import Optional
from dataclasses import dataclass

@dataclass
class APIConfig:
    base_url: str
    api_key: str
    environment: str  # e.g., "development", "production"
    timeouts: Timeouts
    retry_strategy: RetryStrategy
    batch_size: int = 100
    batch_interval: Optional[int] = 5  # seconds, for future batching

def load_config() -> APIConfig:
    # Load from env
    base_url = os.getenv("BASELOG_API_BASE_URL", "https://api.baselog.io/v1")
    api_key = os.getenv("BASELOG_API_KEY")
    if not api_key:
        raise ConfigurationError("BASELOG_API_KEY is required")
    environment = os.getenv("BASELOG_ENVIRONMENT", "development")

    # Load structured components
    timeouts = Timeouts.from_env()  # Custom method to load from env
    retry_strategy = RetryStrategy.from_env()

    return APIConfig(
        base_url=base_url,
        api_key=api_key,
        environment=environment,
        timeouts=timeouts,
        retry_strategy=retry_strategy
    )
```

### Timeouts Dataclass
Structured configuration for HTTP timeouts, converted to dict for `httpx.Timeout`.

```python
from dataclasses import dataclass

@dataclass
class Timeouts:
    connect: float = 10.0
    read: float = 30.0
    write: float = 30.0
    pool: float = 60.0

    @classmethod
    def from_env(cls):
        return cls(
            connect=float(os.getenv("BASELOG_TIMEOUT_CONNECT", "10.0")),
            read=float(os.getenv("BASELOG_TIMEOUT_READ", "30.0")),
            write=float(os.getenv("BASELOG_TIMEOUT_WRITE", "30.0")),
            pool=float(os.getenv("BASELOG_TIMEOUT_POOL", "60.0"))
        )

    def to_dict(self) -> dict:
        return {k: getattr(self, k) for k in self.__dataclass_fields__}
```

### RetryStrategy Dataclass
Configuration for retry logic, used in tenacity decorators for HTTP requests.

```python
from dataclasses import dataclass, field
from typing import List

@dataclass
class RetryStrategy:
    max_attempts: int = 3
    backoff_factor: float = 1.0
    status_forcelist: List[int] = field(default_factory=lambda: [429, 500, 502, 503, 504])
    allowed_methods: List[str] = field(default_factory=lambda: ['POST', 'PUT', 'PATCH'])

    @classmethod
    def from_env(cls):
        return cls(
            max_attempts=int(os.getenv("BASELOG_RETRY_COUNT", "3")),
            backoff_factor=float(os.getenv("BASELOG_RETRY_BACKOFF", "1.0"))
        )

    def to_dict(self) -> dict:
        return {k: getattr(self, k) for k in self.__dataclass_fields__}
```

## Managed Parameters
- **BASELOG_API_BASE_URL** (str): API base URL (default: "https://api.baselog.io/v1"). Used for constructing endpoints like `/projects/logs`.
- **BASELOG_API_KEY** (str): API authentication key (required; raises error if missing). Passed to `auth.py`.
- **BASELOG_ENVIRONMENT** (str): Deployment environment (default: "development"). Can load different profiles (e.g., different URLs per env).
- **BASELOG_TIMEOUT_* ** (float): Individual timeouts (connect/read/write/pool; defaults as above). Fed to `Timeouts` for HTTP client.
- **BASELOG_RETRY_COUNT** (int): Max retry attempts (default: 3). For `RetryStrategy.max_attempts`.
- **BASELOG_RETRY_BACKOFF** (float): Backoff multiplier (default: 1.0). For exponential backoff in retries.
- **BASELOG_BATCH_SIZE** (int): Future batching size (default: 100; not used in Phase 1).
- **BASELOG_BATCH_INTERVAL** (int): Batch send interval in seconds (default: 5; future use).

## Environment Variables Example
```bash
# Basic setup
export BASELOG_API_BASE_URL=https://api.baselog.io/v1
export BASELOG_ENVIRONMENT=production

# Performance tweaks
export BASELOG_TIMEOUT_READ=45  # Longer read timeout for high-latency networks
export BASELOG_RETRY_COUNT=5    # More retries in unreliable environments
```

## Integration with Other Components
- **With `client.py` (Section 1.2):** `load_config()` provides `base_url`, `timeouts.to_dict()`, and `retry_strategy` to initialize `httpx.AsyncClient` and apply retries. Example: `client = APIClient(load_config())`.
- **With `auth.py`:** `config.api_key` is injected into `AuthManager(config.api_key)` for header generation.
- **Error Handling:** Raises `ConfigurationError` (custom exception) for invalid/missing configs. Logs warnings for defaults (e.g., "Using development defaults").
- **Future Extensions:** Support JSON config files or remote config fetching (e.g., via AWS SSM) for advanced setups.

This centralized approach ensures the SDK is configurable, secure, and adaptable to different deployment environments while minimizing configuration errors.