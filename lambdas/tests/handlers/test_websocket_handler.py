import json
from unittest.mock import patch

from handlers.websocket_handler import lambda_handler


@patch("handlers.websocket_handler.websocket_repository.save_connection")
def test_connect_uses_authorizer_identity(mock_save):
    result = lambda_handler(
        {
            "requestContext": {
                "routeKey": "$connect",
                "connectionId": "connection-1",
                "authorizer": {"user_id": "user-123"},
            },
            "queryStringParameters": {"user_id": "attacker-controlled"},
        },
        None,
    )

    assert result["statusCode"] == 200
    mock_save.assert_called_once_with("connection-1", "user-123")


@patch("handlers.websocket_handler.websocket_repository.save_connection")
def test_connect_rejects_missing_authorizer_identity(mock_save):
    result = lambda_handler(
        {
            "requestContext": {
                "routeKey": "$connect",
                "connectionId": "connection-1",
            }
        },
        None,
    )

    assert result["statusCode"] == 401
    mock_save.assert_not_called()


@patch("handlers.websocket_handler._handle_broadcast")
def test_client_cannot_trigger_metrics_broadcast(mock_broadcast):
    result = lambda_handler(
        {
            "requestContext": {
                "routeKey": "$default",
                "connectionId": "connection-1",
            },
            "body": json.dumps({"action": "broadcast_metrics"}),
        },
        None,
    )

    assert result["statusCode"] == 200
    mock_broadcast.assert_not_called()


@patch("handlers.websocket_handler.websocket_repository.update_last_ping")
def test_ping_refreshes_connection_ttl(mock_ping):
    result = lambda_handler(
        {
            "requestContext": {
                "routeKey": "$default",
                "connectionId": "connection-1",
            },
            "body": json.dumps({"action": "ping"}),
        },
        None,
    )

    assert result["statusCode"] == 200
    mock_ping.assert_called_once_with("connection-1")
