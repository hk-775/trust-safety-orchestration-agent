import json
from unittest.mock import MagicMock, patch

from processors import notification_processor


def _record(message_id="message-1", **overrides):
    body = {
        "notification_id": "NOTIFY-01H00000000000000000000000",
        "user_id": "user/123",
        "notification_type": "enforcement",
        "channel": "in_app",
        "subject": "Account update",
        "body": "An action was applied.",
        **overrides,
    }
    return {
        "messageId": message_id,
        "body": json.dumps(body),
    }


@patch("processors.notification_processor.audit_repository.write_log")
@patch("processors.notification_processor.urllib.request.urlopen")
def test_delivers_notification_once_without_requeueing(mock_urlopen, mock_audit, monkeypatch):
    monkeypatch.setenv("PLATFORM_USER_API_URL", "https://platform.example.test/users")
    response = MagicMock()
    response.status = 202
    mock_urlopen.return_value.__enter__.return_value = response

    result = notification_processor.lambda_handler(
        {"Records": [_record()]},
        MagicMock(),
    )

    assert result == {"batchItemFailures": []}
    request = mock_urlopen.call_args.args[0]
    assert request.full_url == "https://platform.example.test/users/user%2F123/notifications"
    assert request.get_method() == "POST"
    assert request.get_header("Idempotency-key") == "NOTIFY-01H00000000000000000000000"
    assert json.loads(request.data)["notification_type"] == "enforcement"
    mock_urlopen.assert_called_once_with(request, timeout=15)
    mock_audit.assert_called_once()
    assert mock_audit.call_args.kwargs["event_type"] == "notification_delivered"


@patch("processors.notification_processor.audit_repository.write_log")
@patch("processors.notification_processor.urllib.request.urlopen")
def test_failed_delivery_is_returned_for_sqs_retry(mock_urlopen, mock_audit, monkeypatch):
    monkeypatch.setenv("PLATFORM_USER_API_URL", "http://platform.example.test/users")

    result = notification_processor.lambda_handler(
        {"Records": [_record(message_id="retry-me")]},
        MagicMock(),
    )

    assert result == {"batchItemFailures": [{"itemIdentifier": "retry-me"}]}
    mock_urlopen.assert_not_called()
    mock_audit.assert_not_called()


@patch("processors.notification_processor.audit_repository.write_log")
@patch("processors.notification_processor.urllib.request.urlopen")
def test_malformed_notification_is_returned_for_sqs_retry(mock_urlopen, mock_audit, monkeypatch):
    monkeypatch.setenv("PLATFORM_USER_API_URL", "https://platform.example.test/users")

    result = notification_processor.lambda_handler(
        {"Records": [_record(message_id="missing-channel", channel=None)]},
        MagicMock(),
    )

    assert result == {"batchItemFailures": [{"itemIdentifier": "missing-channel"}]}
    mock_urlopen.assert_not_called()
    mock_audit.assert_not_called()
