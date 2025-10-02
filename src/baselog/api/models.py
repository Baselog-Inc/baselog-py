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