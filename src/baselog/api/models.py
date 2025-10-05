from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


# Custom Exception Classes
class LogModelError(Exception):
    """Base exception for LogModel validation errors"""
    pass


class InvalidLogLevelError(LogModelError):
    """Raised when an invalid log level is provided"""

    def __init__(self, level: str, valid_levels: list[str]):
        self.level = level
        self.valid_levels = valid_levels
        super().__init__(f"Invalid log level: '{level}'. Must be one of {valid_levels}")


class MissingMessageError(LogModelError):
    """Raised when a log message is missing"""

    def __init__(self):
        super().__init__("Message is required for LogModel")


class LogLevel(str, Enum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

    @classmethod
    def from_string(cls, value: str) -> 'LogLevel':
        """Convert string to LogLevel, case-insensitive"""
        try:
            return cls(value.lower())
        except ValueError:
            raise InvalidLogLevelError(value, [e.value for e in cls])

@dataclass
class LogModel:
    level: LogLevel
    message: str
    category: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    correlation_id: Optional[str] = None

    def __post_init__(self):
        if isinstance(self.level, str):
            self.level = LogLevel.from_string(self.level)
        elif not isinstance(self.level, LogLevel):
            raise InvalidLogLevelError(str(self.level), [e.value for e in LogLevel])
        if not self.message:
            raise MissingMessageError()

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


@dataclass
class APIResponse:
    """Standard API response wrapper."""
    success: bool
    data: Any
    request_id: Optional[str] = None
    timestamp: Optional[str] = None
    message: Optional[str] = None


@dataclass
class LogResponse:
    """Response for log submission."""
    success: bool
    message: str
    data: Dict[str, Any]
    request_id: Optional[str] = None
    timestamp: Optional[str] = None
    correlation_id: Optional[str] = None