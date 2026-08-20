import json
from unittest.mock import MagicMock, patch

from services import notification_service


@patch("services.notification_service.audit_repository.write_log")
@patch("services.notification_service._get_sqs_client")
def test_enforcement_notifications_use_standard_queue_messages(mock_get_client, mock_audit):
    client = MagicMock()
    client.send_message.side_effect = [
        {"MessageId": "in-app-message"},
        {"MessageId": "email-message"},
    ]
    mock_get_client.return_value = client
    mock_audit.return_value = "audit-1"

    result = notification_service.send_enforcement_notification(
        user_id="user-1",
        enforcement_id="CASE-1",
        violation_type="scam",
        action="permanent_ban",
    )

    assert result["in_app_message_id"] == "in-app-message"
    assert result["email_message_id"] == "email-message"
    assert client.send_message.call_count == 2
    for call in client.send_message.call_args_list:
        assert set(call.kwargs) == {"QueueUrl", "MessageBody"}
        message = json.loads(call.kwargs["MessageBody"])
        assert message["notification_id"].startswith("NOTIFY-")
        assert message["user_id"] == "user-1"
        assert message["channel"] in {"in_app", "email"}

    assert mock_audit.call_args.kwargs["event_type"] == "notification_queued"
