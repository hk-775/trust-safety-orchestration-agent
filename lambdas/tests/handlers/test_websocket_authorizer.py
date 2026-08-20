from unittest.mock import patch

from handlers.websocket_authorizer import lambda_handler


@patch("handlers.websocket_authorizer.websocket_ticket_repository.consume_ticket")
def test_allows_valid_one_time_ticket(mock_consume):
    mock_consume.return_value = {"user_id": "user-123", "role": "reviewer"}

    result = lambda_handler(
        {
            "methodArn": "arn:aws:execute-api:us-east-1:123:api/dev/$connect",
            "queryStringParameters": {"ticket": "one-time-ticket"},
        },
        None,
    )

    assert result["principalId"] == "user-123"
    assert result["policyDocument"]["Statement"][0]["Effect"] == "Allow"
    assert result["context"] == {"user_id": "user-123", "role": "reviewer"}
    mock_consume.assert_called_once_with("one-time-ticket")


@patch("handlers.websocket_authorizer.websocket_ticket_repository.consume_ticket")
def test_denies_missing_ticket_without_repository_call(mock_consume):
    result = lambda_handler(
        {"methodArn": "arn:aws:execute-api:us-east-1:123:api/dev/$connect"},
        None,
    )

    assert result["policyDocument"]["Statement"][0]["Effect"] == "Deny"
    mock_consume.assert_not_called()
