# Enhancement: Implement Response and Error Models with Advanced Typing (responses.py)

## Description

This issue proposes the implementation of structured models for incoming API responses and errors in the baselog SDK. Currently, API responses from endpoints like `/projects/logs` are parsed as generic dicts, leading to untyped data and potential runtime errors when accessing fields (e.g., response['id'] without safety). We need defined models to ensure type safety, consistent error handling, and clean parsing of backend responses, including advanced typing for known success structures using TypedDict.

### Problem
- Raw response.json() returns untyped dicts, causing KeyError or AttributeError at runtime (e.g., accessing non-existent 'created_at').
- No standardized error structure; errors from httpx are not mapped to SDK-specific types, making debugging harder.
- IDE lacks autocompletion for response fields (e.g., data.id, data.project_id).
- Future-proofing for typed responses is missing; generic Dict[str, Any] hides backend schema (id, project_id, level, etc.).

### Proposed Solution
Introduce `responses.py` with dataclasses for response/error models:
- **APIResponse:** For success (2xx) responses; data: Optional[LogResponse] for typed log creation.
- **APIError:** For errors (non-2xx), capturing code, message, details, HTTP status, retry_after.
- **LogResponse TypedDict:** Precise type for APIResponse.data in success cases from `/projects/logs`.
- Validation: Factory methods for parsing; type guards for safety.
- Integration: Client methods return APIResponse or raise APIError; fallback in Logger on errors.

This ensures typed, reliable response handling.

### Implementation
1. **Create responses.py:**
   - Imports: dataclasses, typing (Optional, Dict, TypedDict, List), datetime.
   - Define TypedDict LogResponse for known schema.
   - Define dataclasses APIResponse and APIError with from_success_response and from_http_error factories.

   **Full Implementation Code Block:**
   ```python
   # responses.py
   from dataclasses import dataclass, field
   from typing import Optional, Dict, Any, TypedDict, List
   from datetime import datetime

   class LogResponse(TypedDict):
       id: str  # Generated log ID
       project_id: str  # Associated project
       level: str  # Echoed from request
       category: str
       message: str
       tags: List[str]  # Echoed from request
       created_at: str  # ISO 8601, e.g., "2025-09-30T05:47:54.589Z"
       updated_at: str  # ISO 8601, typically same as created_at for new logs

   @dataclass
   class APIResponse:
       success: bool
       data: Optional[LogResponse] = None  # Typed for log success
       message: Optional[str] = None
       request_id: Optional[str] = None
       timestamp: datetime = field(default_factory=datetime.utcnow)

       @classmethod
       def from_success_response(cls, response):
           """Parse successful HTTP response (2xx)."""
           try:
               data = LogResponse(response.json()) if response.json() else None
           except (ValueError, KeyError):
               raise ValueError("Invalid response structure")
           return cls(success=True, data=data, request_id=response.headers.get("X-Request-ID"))

   @dataclass
   class APIError:
       error_code: str  # e.g., "INVALID_API_KEY"
       message: str  # Human-readable error
       details: Optional[Dict[str, Any]] = None  # Extra info
       http_status: int  # e.g., 401
       retry_after: Optional[int] = None  # For rate limiting

       @classmethod
       def from_http_error(cls, response):
           """Map HTTP error response to APIError."""
           try:
               json_data = response.json()
           except ValueError:
               json_data = {"message": "Unknown error"}
           retry_after = None
           if "Retry-After" in response.headers:
               retry_after = int(response.headers["Retry-After"])
           return cls(
               error_code=json_data.get("code", "UNKNOWN_ERROR"),
               message=json_data.get("message", "API Error"),
               details=json_data,
               http_status=response.status_code,
               retry_after=retry_after
           )
   ```

2. **Client Integration:**
   - In client.py: After POST, if response.status_code == 201, return `APIResponse.from_success_response(response)`.
   - On error (e.g., in except httpx.HTTPStatusError as e): raise `APIError.from_http_error(e.response)`.
   - Add to send_log: Try/except for handling.

3. **Typing and Parsing:**
   - Use LogResponse for data in log success; mypy ensures safe access.
   - Type guards: `if response.success and response.data: response.data.id`.

4. **Validation:** Factories check JSON structure; raise ValueError on invalid.

5. **Dependencies:** Stdlib (dataclasses 3.7+, typing 3.9+ for TypedDict).

### Benefits
- **Type Safety:** mypy catches 'data.invalid_field'; IDE shows data.id.
- **Error Handling:** Standardized APIError with http_status for retries.
- **Backend Match:** LogResponse exactly fits API response, minimizing parse errors.
- **Ease of Use:** Factories simplify client code; clear success/failure paths.
- **Performance:** Fast parsing with no overhead.

### Alternatives Considered
- **Generic Dict:** Simple but no typing; hard to debug.
- **Pydantic:** Auto-validation but adds dep; defer to Phase 4.
- **Custom Classes:** Dataclasses are lightweight; TypedDict adds type without runtime cost.

**Recommendation:** Dataclasses + TypedDict for Phase 1; Pydantic later.

### Related Issues
- [Link to models.py enhancement for request models]
- Phase 1: Core API; Phase 5: Testing.

### Acceptance Criteria
- Factories parse valid responses (APIResponse from 201, APIError from 401).
- mypy passes with typed data (access data.id OK, data.invalid error).
- send_log uses factories (return APIResponse on success, raise APIError on failure).
- Test coverage 90%+ for parsing/mapping.
- No runtime errors on mock invalid JSON (handled gracefully).

Assign to: [Developer]
Priority: High (Phase 1 for API responses)
Labels: enhancement, api, typing

## Testing the Response Models
The response models (APIResponse, APIError, LogResponse) should be tested for parsing, error mapping, type safety, and integration.

### Unit Tests for Parsing and Construction (pytest)
- **APIResponse:**
  - Successful from_success_response with mock 201 JSON (LogResponse-like); verify data is LogResponse with id, created_at.
  - Empty data: 204 response ’ data=None, success=True.
  - Timestamp auto-set: Verify default datetime.
- **APIError:**
  - from_http_error with mock 401 JSON ({"code": "UNAUTH"}); verify error_code, message, http_status.
  - Retry-After header: Set retry_after from headers.
  - Generic fallback: No JSON ’ default "UNKNOWN_ERROR".

### Serialization/Deserialization Tests
- **LogResponse TypedDict:** From JSON dict; mypy verifies structure (static).
- **Parsing Edge:** Malformed JSON ’ raise ValueError in factory.

### Type Safety Tests (mypy)
- **LogResponse:** Valid access (data.id); invalid (data.invalid) ’ mypy error.
- **APIResponse:** data.project_id with Optional; type guards OK.
- Run mypy on responses.py + client.py.

### Integration Tests (pytest with mock httpx)
- **Success Parsing:** Mock POST 201 with full LogResponse body; verify send_log returns APIResponse with typed data.
- **Error Mapping:** Mock 429 with Retry-After header; verify APIError(retry_after set), raise in test.
- **Edge Cases:** 500 (server error) ’ APIError; no content ’ data=None.

### Other Considerations
- **Coverage:** 95%+ for factories, parsing, raises.
- **Fixtures:** Mock httpx responses, LogResponse dicts.
- **Tools:** pytest, mypy, httpx mocks.
- Links: Unit here; full client integration.

These tests ensure safe, typed response handling without runtime surprises in Phase 1.