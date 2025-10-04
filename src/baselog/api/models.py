from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class LogLevel(Enum):
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
            raise ValueError(f"Invalid log level: {value}. Must be one of {[e.value for e in cls]}")

@dataclass
class LogModel:
    level: LogLevel
    message: str
    category: Optional[str] = None
    tags: List[str] = field(default_factory=list)

    def __post_init__(self):
        if not self.message:
            raise ValueError("Message is required for LogModel")

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