# 1.3 Data Models Documentation

This file documents the data models used in the baselog API integration, covering serialization models for requests (in `models.py`) and response/error models (in `responses.py`). Models are defined using dataclasses for runtime validation and type hints. Advanced typing with `TypedDict` is recommended for response data to match the backend's known schema.

## Overview
- **Purpose:** These models ensure structured data exchange with the backend, prevent runtime errors, and enable IDE autocompletion.
- **Dependencies:** `dataclasses`, `typing` (for Optional, List, Dict, Any), `field` for defaults, and optionally `pydantic` for validation.
- **Key Principles:**
  - Minimal required fields for backend compatibility.
  - Optional enhancements added by the client (e.g., timestamp).
  - Generic Dict for flexible errors; typed for known success responses.

## Request Models (`models.py`)

### Role
Strict definition of data structures for outgoing API requests (e.g., logs sent to `/projects/logs`).

### LogModel (Structure)
Designed to match the backend's minimal schema: `level`, `message`, `category`, `tags`. Optional fields are client enhancements.

```python
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime

@dataclass
class LogModel:
    level: str  # e.g., "info", "error" (string as per backend)
    message: str
    category: Optional[str] = None  # Required in spec but optional in model
    tags: List[str] = field(default_factory=list)
```

- **Usage Notes:**
  - Map from Logger: `LogModel(level="info", message=msg, category=cat, tags=tags)`.
  - Serialization: Use `log_data.dict(exclude_unset=True)` for JSON, excluding unset optionals.
  - Validation: Add runtime checks (e.g., `level in {"info", "error", ...}`).

### EventModel (Structure)
Placeholder for future event support (not yet available in backend).

```python
@dataclass
class EventModel:
    event_type: str
    payload: Dict[str, Any]
    timestamp: datetime  # Auto-filled if needed
    source_service: str
    user_id: Optional[str] = None
    correlation_id: Optional[str] = None
```

- **Usage Notes:** Reserved; `send_event` will raise NotImplementedError in Phase 1.

## Response and Error Models (`responses.py`)

### Role
Normalization of incoming API responses and standardized error handling. Ensures consistent structure across success/error cases.

### APIResponse (Success Response)
Generic base; see advanced typing below for precision.

```python
@dataclass
class APIResponse:
    success: bool
    data: Optional[Dict[str, Any]] = None  # Typed as LogResponse for log creation
    message: Optional[str] = None
    request_id: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
```

- **Parsing:** From `response.json()`: `APIResponse(success=True if 2xx else False, data=response.json())`.
- **For Log Creation:** `data` contains the created log object (e.g., with `id`, `created_at`).

### APIError (Error Response)
For non-2xx responses, capturing backend error details.

```python
@dataclass
class APIError:
    error_code: str  # e.g., "INVALID_API_KEY"
    message: str  # Human-readable error
    details: Optional[Dict[str, Any]] = None  # Extra info (generic for varying errors)
    http_status: int  # e.g., 401, 429
    retry_after: Optional[int] = None  # Seconds for rate limiting (from header)
```

- **Usage Notes:**
  - Mapped from `httpx.HTTPStatusError`: `APIError(error_code=response.json().get('code'), http_status=response.status_code)`.
  - Specific subtypes: Inherit for `APIAuthenticationError(APIError, http_status=401)`, etc.

## Advanced Typing: Improving APIResponse.data

To enhance type safety beyond `Optional[Dict[str, Any]]`, use `TypedDict` for the known success response structure from `/projects/logs`. This provides compile-time checks and better IDE support.

### LogResponse TypedDict
Defines the exact shape of the created log object returned on success.

```python
from typing import TypedDict, List

class LogResponse(TypedDict):
    id: str  # Generated log ID
    project_id: str  # Associated project
    level: str  # Echoed from request
    category: str
    message: str
    tags: List[str]  # Echoed from request
    created_at: str  # ISO 8601, e.g., "2025-09-30T05:47:54.589Z"
    updated_at: str  # ISO 8601, typically same as created_at for new logs
```

### Updated APIResponse with Typed Data
Replace the generic `data` with `LogResponse` for log-specific responses.

```python
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class APIResponse:
    success: bool
    data: Optional[LogResponse] = None  # Precise typing for success
    message: Optional[str] = None
    request_id: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
```

### Benefits of TypedDict
- **Type Checking:** Tools like mypy catch misuse (e.g., `data.foo` if "foo" not in LogResponse).
- **IDE Support:** Autocompletion for fields like `data.id` or `data.created_at`.
- **Validation:** Optional: Use `pydantic.validate(LogResponse, response_data)` at runtime.
- **Error Details:** Keep `APIError.details` as `Dict[str, Any]` since error shapes vary (e.g., {"validation_errors": {...}}).

### Usage Example in `send_log`
```python
async def send_log(self, log_data: LogModel) -> APIResponse:
    # ... (POST request logic)
    if response.status_code == 201:  # Success for creation
        response_data = response.json()
        # Optional type cast for safety
        if isinstance(response_data, dict):
            data = LogResponse(response_data)  # mypy verifies structure
        return APIResponse(success=True, data=data, request_id=response.headers.get("X-Request-ID"))
    else:
        raise APIError.from_response(response)  # Handled in caller
```

This organization provides a clear progression from request models to typed responses, making the API integration more robust and developer-friendly.

## Testing the Data Models

### Testing Requirements
The data models (LogModel, EventModel, APIResponse, APIError, and LogResponse TypedDict) should be thoroughly tested for validation, serialization, type safety, and integration with API responses. Focus on unit tests with pytest, type checking with mypy, and basic integration tests. Aim for 95%+ coverage to ensure robustness and backend compatibility.

#### 1. Unit Tests for Validation and Construction (pytest)
- **LogModel:**
  - Successful instantiation with required fields (level="info", message="test"); verify defaults (tags=[], category=None).
  - Required field checks: Raise ValueError if message is empty or level is invalid (e.g., "" or None).
  - Optional fields: Ensure category/tags accept None or empty lists without errors.
- **EventModel:**
  - Stub test: Instantiate with event_type and payload; verify NotImplementedError if send_event is called (linked to client).
  - Future validation: Test auto-fill for timestamp if not set, payload accepts any dict.
- **APIResponse and APIError:**
  - Construction: APIResponse(success=True, data={"key": "value"}); APIError(error_code="INVALID", http_status=400) – verify attributes.
  - Equality/Comparison: assert APIResponse(success=True) != APIResponse(success=False).

#### 2. Serialization/Deserialization Tests (pytest with json)
- **LogModel:**
  - To Dict/JSON: log_data = LogModel(level="info", message="test", tags=["tag1"]); assert log_data.dict() == {"level": "info", "message": "test", "tags": ["tag1"]}.
  - From Dict: Create from backend-like dict; verify reconstruction.
  - Exclude Optionals: exclude_unset=True to send only set fields (critical for strict backend).
- **APIResponse/APIError:**
  - From Response JSON: Simulate response.json() → parse into APIResponse(data=LogResponse({"id": "123", ...})).
  - Error Parsing: From mock HTTP response (status 401, json={"code": "UNAUTH"}) → APIError(error_code="UNAUTH", http_status=401).
  - TypedDict: log_resp = LogResponse({"id": "123", "project_id": "abc", ...}); verify mypy no errors (static test).

#### 3. Type Safety Tests (mypy)
- **LogResponse TypedDict:**
  - Valid access: data.id, data.tags[0] – mypy OK.
  - Invalid access: data.invalid_field – mypy error to catch dev-time issues.
  - In APIResponse: response.data.project_id with Optional[LogResponse]; mypy infers type guards (e.g., if response.data).
- **General:** Run mypy on the module; ensure None/Optionals do not cause false positives.
- **Optional Pydantic:** If added, test LogResponse.parse_obj(response_data) raises ValidationError on mismatch (e.g., tags not list).

#### 4. Integration Tests (pytest with mock httpx)
- **Response Parsing:** Mock POST /projects/logs → response 201 with LogResponse-like body; verify APIResponse(data=LogResponse(mock_data)) has correct fields (id, created_at).
- **Error Parsing:** Mock 429 → parse into APIError(retry_after=60 from header); verify retry_after set.
- **Edge Cases:**
  - Empty Response: 204 No Content → APIResponse(success=True, data=None).
  - Malformed JSON: Raise JSONDecodeError → map to APIError.
  - Type Mismatch: Backend returns level as int (error) → Pydantic reject if used; fallback to Dict.
- **Tools:** httpx.MockTransport for simulated responses without real HTTP; pytest-asyncio for async methods (sync sufficient for models).

#### 5. Other Considerations
- **Coverage:** Target 95%+ (test all fields, defaults, raises).
- **Fixtures:** pytest fixtures for mock configs (LogModel fixture, mock response dict).
- **Performance:** Not critical for models, but timeit .dict() for 1k logs to ensure fast serialization.
- **Links to Client:** Unit tests here; integration in client tests (e.g., send_log → parse to APIResponse).
- **Tools Recommended:** pytest, mypy, coverage.py; optional Pydantic for runtime validation.

These tests cover risks (validation failure, parse errors, type safety) without overloading Phase 1. They can be added in Phase 5 (testing).