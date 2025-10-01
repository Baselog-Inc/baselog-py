# Enhancement: Implement Strict Request Models for API Integration (models.py)

## Description

This issue proposes the implementation of strict data models for outgoing API requests in the baselog SDK. Currently, log data is passed as loose parameters to the Logger methods, which works for console output but lacks structure for API serialization. We need defined models to ensure type safety, validation, and clean JSON mapping for the backend `/projects/logs` endpoint.

### Problem
- No typed structure for log data, leading to potential runtime errors (e.g., missing message or invalid level).
- Direct parameter passing in Logger doesn't scale for future enhancements (e.g., events).
- Serialization to JSON for HTTP POST is ad-hoc, risking mismatches with backend schema (level, message, category, tags as strings/array).
- IDE lacks autocompletion and validation for log payloads.

### Proposed Solution
Introduce `models.py` with dataclasses for request models:
- **LogModel:** Minimal fields matching backend: level (str, e.g., "info"), message (str, required), category (Optional[str]), tags (List[str] with default empty).
- **EventModel:** Placeholder for future (event_type: str, payload: Dict, timestamp: datetime, etc.).
- Use `dataclasses` for easy `.dict()` serialization (via `asdict` or Pydantic integration if added).
- Validation: Runtime checks for required fields; optional Pydantic for full schema enforcement.
- Integration: Logger methods create LogModel from kwargs, pass to `APIClient.send_log`.

This keeps the public API simple (e.g., `logger.info("msg", category="cat")`) while internalizing structure.

### Implementation
1. **Create models.py:**
   - Import dataclasses, typing (Optional, List, Dict), datetime.
   - Define LogModel as dataclass with fields:
     - level: str  # e.g., "info", "error"
     - message: str
     - category: Optional[str] = None
     - tags: List[str] = field(default_factory=list)
   - Define EventModel as placeholder:
     - event_type: str
     - payload: Dict[str, Any]
     - timestamp: datetime
     - source_service: str
     - user_id: Optional[str] = None
     - correlation_id: Optional[str] = None

   **Full Implementation Code Block:**
   ```python
   # models.py
   from dataclasses import dataclass, field
   from typing import Optional, List, Dict, Any
   from datetime import datetime

   @dataclass
   class LogModel:
       level: str  # e.g., "info", "error"
       message: str
       category: Optional[str] = None
       tags: List[str] = field(default_factory=list)

       def __post_init__(self):
           if not self.message:
               raise ValueError("Message is required for LogModel")
           valid_levels = {"info", "debug", "warning", "error", "critical"}
           if self.level.lower() not in valid_levels:
               raise ValueError(f"Invalid level: {self.level}. Must be one of {valid_levels}")

   @dataclass
   class EventModel:
       event_type: str
       payload: Dict[str, Any]
       timestamp: datetime
       source_service: str
       user_id: Optional[str] = None
       correlation_id: Optional[str] = None

       def __post_init__(self):
           if not self.event_type:
               raise ValueError("Event type is required")
           if not self.payload:
               raise ValueError("Payload is required for EventModel")
   ```

2. **Logger Integration:**
   - In logger.py: `def info(self, message: str, category: Optional[str] = None, tags: List[str] = []): log_data = LogModel(level="info", message=message, category=category, tags=tags)`.
   - Pass to client: `await self.client.send_log(log_data)`.

3. **Serialization:** Use `log_data.__dict__` or `dataclasses.asdict(log_data)` for JSON; exclude_unset if using Pydantic.

4. **Validation:** Add in LogModel.__post_init__: if not message: raise ValueError("Message required").

5. **Dependencies:** None new; uses stdlib (dataclasses from 3.7+).

### Benefits
- **Type Safety:** IDE autocompletion for Logger kwargs; mypy catches misuse.
- **Backend Compatibility:** Exact match to POST body schema, reducing 400 errors.
- **Maintainability:** Centralized models for future changes (e.g., add fields if backend evolves).
- **Performance:** Minimal overhead (dataclass is lightweight); serialization ~1μs per log.
- **Developer Experience:** Clear docstrings and types improve SDK usability.

### Alternatives Considered
- **Loose Dict:** Pass dict to client; simpler but no validation/type hints.
- **Pydantic Models:** More powerful validation but adds dependency (heavier for Phase 1).
- **NamedTuple:** Lighter than dataclass but immutable and less flexible for defaults.

**Recommendation:** Start with dataclasses; upgrade to Pydantic in Phase 4 if needed for complex validation.

### Related Issues
- # [Link to client.py enhancement]
- Phase 1: Core API integration.

### Acceptance Criteria
- LogModel created from Logger kwargs matches backend schema.
- send_log serializes to correct JSON (test with mock).
- Raise on missing required fields.
- mypy passes on Logger + models.
- 90%+ test coverage for models (unit: validation/serialization).

Assign to: [Developer]
Priority: High (Phase 1 blocker for API logging)
Labels: enhancement, api, typing

## Testing Plan

### Testing Requirements
The data models (LogModel, EventModel) and their integration should be thoroughly tested for validation, serialization, type safety, and usage in API calls. Focus on unit tests with pytest, type checking with mypy, and basic integration tests. Aim for 95%+ coverage to ensure robustness and backend compatibility.

#### 1. Unit Tests for Validation and Construction (pytest)
- **LogModel:**
  - Successful instantiation with required fields (level="info", message="test"); verify defaults (tags=[], category=None).
  - Required field checks: Raise ValueError if message is empty or level is invalid (e.g., "" or None).
  - Optional fields: Ensure category/tags accept None or empty lists without errors.
  - __post_init__ validation: Test raises for invalid levels (e.g., "invalid") and missing message.
- **EventModel:**
  - Stub test: Instantiate with event_type and payload; verify raises ValueError if event_type or payload empty.
  - Future validation: Test auto-fill for timestamp if not set, payload accepts any dict without errors.

#### 2. Serialization/Deserialization Tests (pytest with json)
- **LogModel:**
  - To Dict/JSON: log_data = LogModel(level="info", message="test", tags=["tag1"]); assert log_data.__dict__ or asdict(log_data) == {"level": "info", "message": "test", "tags": ["tag1"]}.
  - From Dict: Create from backend-like dict; verify reconstruction and validation passes.
  - Exclude Optionals: Test serialization excludes None category if unset.
- **EventModel:**
  - To Dict: Verify payload as dict is preserved; timestamp serialized as ISO string if needed.

#### 3. Type Safety Tests (mypy)
- **LogModel/EventModel:**
  - Valid access: log_data.message, event_data.payload["key"] – mypy OK.
  - Invalid access: log_data.invalid – mypy error to catch dev-time issues.
  - In Logger: mypy passes on logger.info calls with typed kwargs.
- **General:** Run mypy on models.py and logger.py; ensure Optionals do not cause false positives.

#### 4. Integration Tests (pytest with mock httpx or client mocks)
- **Model in API Call:** Mock APIClient.send_log(log_data) → verify serialized JSON matches backend schema (e.g., {"level": "info", "message": "test", ...}).
- **Error Cases:** Pass invalid LogModel to send_log → verify raise propagates correctly.
- **Edge Cases:**
  - Empty tags: Serialize as [] without error.
  - Long message: No truncation; backend handles.
- **Tools:** Mock APIClient for unit-like integration; httpx.MockTransport if full client test.

#### 5. Other Considerations
- **Coverage:** Target 95%+ (test all fields, defaults, raises in __post_init__).
- **Fixtures:** pytest fixtures for common LogModel (valid/invalid), mock config.
- **Performance:** Timeit serialization for 1k logs (~1μs per log expected).
- **Links to Other Components:** Unit tests here; integration with client.py tests (e.g., end-to-end send_log with model).
- **Tools Recommended:** pytest for runtime, mypy for static typing, coverage.py for metrics; optional Pydantic for advanced validation tests.

These tests will validate the models' correctness, ensuring seamless integration with the backend and no runtime surprises in Phase 1.