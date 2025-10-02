from dataclasses import dataclass, field
from typing import Optional, Dict, Any, TypedDict, List
from datetime import datetime, timezone


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
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @classmethod
    def from_success_response(cls, response):
        try:
            json_data = response.json()
            data = None
            if json_data is not None:
                required_keys = {"id", "project_id", "level", "category", "message", "tags", "created_at", "updated_at"}
                if not all(key in json_data for key in required_keys):
                    raise ValueError("Invalid response structure")
                data = json_data
        except (ValueError, KeyError):
            raise ValueError("Invalid response structure")
        return cls(
            success=True, data=data, request_id=response.headers.get("X-Request-ID")
        )


@dataclass
class APIError:
    error_code: str  # e.g., "INVALID_API_KEY"
    message: str  # Human-readable error
    http_status: int  # e.g., 401
    details: Optional[Dict[str, Any]] = None  # Extra info
    retry_after: Optional[int] = None  # For rate limiting

    @classmethod
    def from_http_error(cls, response):
        try:
            json_data = response.json()
        except ValueError:
            json_data = {"message": "Unknown error"}
        retry_after = None
        retry_after = None
        if "Retry-After" in response.headers:
            try:
                retry_after = int(response.headers["Retry-After"])
            except (ValueError, TypeError):
                pass  # Invalid retry_after format, leave as None
        return cls(
            error_code=json_data.get("code", "UNKNOWN_ERROR"),
            message=json_data.get("message", "API Error"),
            details=json_data,
            http_status=response.status_code,
            retry_after=retry_after,
        )
