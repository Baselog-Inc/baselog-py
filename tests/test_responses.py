import pytest
from unittest.mock import Mock, MagicMock
from baselog.api.responses import APIResponse, APIError, LogResponse

def test_apiresponse_from_success_response_valid():
    mock_response = MagicMock()
    mock_json = {
        "id": "log123",
        "project_id": "proj456",
        "level": "info",
        "category": "test",
        "message": "Test log",
        "tags": ["tag1"],
        "created_at": "2025-09-30T05:47:54.589Z",
        "updated_at": "2025-09-30T05:47:54.589Z"
    }
    mock_response.json.return_value = mock_json
    mock_response.headers.get.return_value = "req-id-789"
    mock_response.status_code = 201

    api_resp = APIResponse.from_success_response(mock_response)

    assert api_resp.success is True
    assert api_resp.data == mock_json
    assert api_resp.request_id == "req-id-789"

def test_apiresponse_from_success_response_empty_data():
    mock_response = MagicMock()
    mock_response.json.return_value = None
    mock_response.headers.get.return_value = None
    mock_response.status_code = 204

    api_resp = APIResponse.from_success_response(mock_response)

    assert api_resp.success is True
    assert api_resp.data is None
    assert api_resp.request_id is None

def test_apiresponse_from_success_response_invalid_structure():
    mock_response = MagicMock()
    mock_response.json.return_value = {"invalid": "data"}
    mock_response.status_code = 200

    with pytest.raises(ValueError, match="Invalid response structure"):
        APIResponse.from_success_response(mock_response)

def test_apierror_from_http_error_with_json():
    mock_response = MagicMock()
    mock_json = {
        "code": "UNAUTH",
        "message": "Unauthorized access"
    }
    mock_response.json.return_value = mock_json
    mock_response.status_code = 401
    mock_response.headers.get.return_value = None  # No Retry-After

    api_error = APIError.from_http_error(mock_response)

    assert api_error.error_code == "UNAUTH"
    assert api_error.message == "Unauthorized access"
    assert api_error.details == mock_json
    assert api_error.http_status == 401
    assert api_error.retry_after is None

def test_apierror_from_http_error_with_retry_after():
    mock_response = MagicMock()
    mock_json = {"code": "RATE_LIMIT", "message": "Too many requests"}
    mock_response.json.return_value = mock_json
    mock_response.status_code = 429
    mock_response.headers = {"Retry-After": "60"}

    api_error = APIError.from_http_error(mock_response)

    assert api_error.retry_after == 60

def test_apierror_from_http_error_no_json():
    mock_response = MagicMock()
    mock_response.json.side_effect = ValueError("Invalid JSON")
    mock_response.status_code = 500
    mock_response.headers = {}

    api_error = APIError.from_http_error(mock_response)

    assert api_error.error_code == "UNKNOWN_ERROR"
    assert api_error.message == "Unknown error"
    assert api_error.details == {"message": "Unknown error"}
    assert api_error.http_status == 500
    assert api_error.retry_after is None

def test_apierror_fallback_message():
    mock_response = MagicMock()
    mock_response.json.return_value = {"code": "ERR", "details": "info"}  # No message
    mock_response.status_code = 400
    mock_response.headers = {}

    api_error = APIError.from_http_error(mock_response)

    assert api_error.message == "API Error"

def test_logresponse_type_check():
    # Static type check via runtime assertion (mypy would catch static)
    log_data = LogResponse({
        "id": "test-id",
        "project_id": "test-proj",
        "level": "info",
        "category": "cat",
        "message": "msg",
        "tags": ["tag"],
        "created_at": "2023-01-01T00:00:00Z",
        "updated_at": "2023-01-01T00:00:00Z"
    })
    assert isinstance(log_data, dict)  # TypedDict is dict at runtime
    assert "id" in log_data
