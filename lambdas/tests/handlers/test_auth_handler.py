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
