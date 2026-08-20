import json
from unittest.mock import Mock

from handlers import auth_handler


def test_login_returns_only_the_id_token(monkeypatch):
    cognito = Mock()
    cognito.admin_initiate_auth.return_value = {
        "AuthenticationResult": {
            "IdToken": "id-token",
            "AccessToken": "access-token",
            "RefreshToken": "refresh-token",
        }
    }
    cognito.admin_get_user.return_value = {
        "UserAttributes": [
            {"Name": "sub", "Value": "user-123"},
            {"Name": "custom:role", "Value": "admin"},
        ]
    }
    monkeypatch.setattr(auth_handler, "cognito", cognito)

    result = auth_handler.lambda_handler(
        {"body": json.dumps({"email": "admin", "password": "correct-password"})},
        None,
    )

    assert result["statusCode"] == 200
    body = json.loads(result["body"])
    assert body == {
        "token": "id-token",
        "user_id": "user-123",
        "email": "admin",
        "role": "admin",
    }


def test_authenticated_user_can_create_websocket_ticket(api_gateway_event, monkeypatch):
    create_ticket = Mock(
        return_value={"ticket": "one-time-ticket", "expires_at": 1060}
    )
    monkeypatch.setattr(
        auth_handler.websocket_ticket_repository,
        "create_ticket",
        create_ticket,
    )

    result = auth_handler.lambda_handler(
        api_gateway_event(
            method="POST",
            path="/api/v1/auth/websocket-ticket",
            claims={"sub": "user-123", "custom:role": "reviewer"},
        ),
        None,
    )

    assert result["statusCode"] == 200
    assert json.loads(result["body"]) == {
        "ticket": "one-time-ticket",
        "expires_at": 1060,
    }
    create_ticket.assert_called_once_with(user_id="user-123", role="reviewer")


def test_websocket_ticket_requires_cognito_identity(api_gateway_event, monkeypatch):
    create_ticket = Mock()
    monkeypatch.setattr(
        auth_handler.websocket_ticket_repository,
        "create_ticket",
        create_ticket,
    )

    event = api_gateway_event(
        method="POST",
        path="/api/v1/auth/websocket-ticket",
    )
    event["requestContext"]["authorizer"]["claims"] = {}
    result = auth_handler.lambda_handler(event, None)

    assert result["statusCode"] == 401
    create_ticket.assert_not_called()
