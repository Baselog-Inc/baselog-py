import pytest
from datetime import datetime
from dataclasses import asdict
from baselog.api.models import LogModel, EventModel, LogLevel


def test_logmodel_successful_instantiation():
    log = LogModel(level=LogLevel.INFO, message="Test message")
    assert log.level == LogLevel.INFO
    assert log.message == "Test message"
    assert log.category is None
    assert log.tags == []


def test_logmodel_with_optional_fields():
    log = LogModel(
        level=LogLevel.ERROR, message="Test error", category="auth", tags=["tag1", "tag2"]
    )
    assert log.level == LogLevel.ERROR
    assert log.message == "Test error"
    assert log.category == "auth"
    assert log.tags == ["tag1", "tag2"]


def test_logmodel_missing_message():
    with pytest.raises(ValueError, match="Message is required"):
        LogModel(level=LogLevel.INFO, message="")


def test_logmodel_empty_message():
    with pytest.raises(ValueError, match="Message is required"):
        LogModel(level=LogLevel.INFO, message="")


def test_logmodel_invalid_level():
    with pytest.raises(ValueError, match="Invalid log level"):
        LogLevel.from_string("invalid")


def test_logmodel_case_insensitive_level():
    log = LogModel(level=LogLevel.from_string("INFO"), message="Test")
    assert log.level == LogLevel.INFO


def test_logmodel_serialization_to_dict():
    log = LogModel(level=LogLevel.INFO, message="Test", category="test_cat", tags=["one"])
    expected = {
        "level": "info",
        "message": "Test",
        "category": "test_cat",
        "tags": ["one"],
    }
    assert asdict(log) == expected


def test_logmodel_exclude_optionals_none():
    log = LogModel(level=LogLevel.INFO, message="Test")
    serialized = asdict(log)
    assert "category" in serialized  # Includes None
    assert serialized["category"] is None
    assert "tags" in serialized
    assert serialized["tags"] == []


# LogLevel Enum Tests
def test_loglevel_enum_values():
    assert LogLevel.DEBUG.value == "debug"
    assert LogLevel.INFO.value == "info"
    assert LogLevel.WARNING.value == "warning"
    assert LogLevel.ERROR.value == "error"
    assert LogLevel.CRITICAL.value == "critical"


def test_loglevel_from_string_valid():
    assert LogLevel.from_string("debug") == LogLevel.DEBUG
    assert LogLevel.from_string("INFO") == LogLevel.INFO
    assert LogLevel.from_string("Warning") == LogLevel.WARNING
    assert LogLevel.from_string("ERROR") == LogLevel.ERROR
    assert LogLevel.from_string("critical") == LogLevel.CRITICAL


def test_loglevel_from_string_invalid():
    with pytest.raises(ValueError, match="Invalid log level: invalid"):
        LogLevel.from_string("invalid")

    with pytest.raises(ValueError, match="Invalid log level: unknown"):
        LogLevel.from_string("unknown")

    with pytest.raises(ValueError, match="Invalid log level: "):
        LogLevel.from_string("")


def test_loglevel_serialization_value():
    assert LogLevel.INFO.value == "info"
    assert LogLevel.ERROR.value == "error"


def test_loglevel_enum_membership():
    assert LogLevel.DEBUG in LogLevel
    assert LogLevel.INFO in LogLevel
    assert LogLevel.WARNING in LogLevel
    assert LogLevel.ERROR in LogLevel
    assert LogLevel.CRITICAL in LogLevel


def test_eventmodel_successful_instantiation():
    timestamp = datetime.now()
    event = EventModel(
        event_type="user_login",
        payload={"user_id": 123},
        timestamp=timestamp,
        source_service="web",
    )
    assert event.event_type == "user_login"
    assert event.payload == {"user_id": 123}
    assert event.timestamp == timestamp
    assert event.source_service == "web"
    assert event.user_id is None
    assert event.correlation_id is None


def test_eventmodel_with_optionals():
    event = EventModel(
        event_type="user_login",
        payload={"user_id": 123},
        timestamp=datetime.now(),
        source_service="web",
        user_id="user456",
        correlation_id="corr789",
    )
    assert event.user_id == "user456"
    assert event.correlation_id == "corr789"


def test_eventmodel_missing_event_type():
    with pytest.raises(ValueError, match="Event type is required"):
        EventModel(
            event_type="",
            payload={"test": "data"},
            timestamp=datetime.now(),
            source_service="test",
        )


def test_eventmodel_empty_payload():
    with pytest.raises(ValueError, match="Payload is required"):
        EventModel(
            event_type="test_event",
            payload={},
            timestamp=datetime.now(),
            source_service="test",
        )


def test_eventmodel_serialization_to_dict():
    timestamp = datetime.now()
    event = EventModel(
        event_type="test_event",
        payload={"key": "value"},
        timestamp=timestamp,
        source_service="test_service",
    )
    expected = {
        "event_type": "test_event",
        "payload": {"key": "value"},
        "timestamp": timestamp,
        "source_service": "test_service",
        "user_id": None,
        "correlation_id": None,
    }
    assert asdict(event) == expected
