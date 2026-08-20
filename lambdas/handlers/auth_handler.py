import json
import logging
import os

import boto3

from handlers.http_response import response_headers
from repositories import websocket_ticket_repository

logger = logging.getLogger(__name__)

cognito = boto3.client("cognito-idp")
USER_POOL_ID = os.environ.get("USER_POOL_ID", "")
CLIENT_ID = os.environ.get("CLIENT_ID", "")


def lambda_handler(event, context):
    try:
        if _is_websocket_ticket_request(event):
            return _create_websocket_ticket(event)

        body = json.loads(event.get("body") or "{}")
        email = body.get("email", "").strip()
        password = body.get("password", "")

        if not email or not password:
            return _response(400, {"error": "Email and password are required"})

        auth_result = cognito.admin_initiate_auth(
            UserPoolId=USER_POOL_ID,
            ClientId=CLIENT_ID,
            AuthFlow="ADMIN_USER_PASSWORD_AUTH",
            AuthParameters={"USERNAME": email, "PASSWORD": password},
        )

        if auth_result.get("ChallengeName"):
            return _response(401, {"error": "Account requires additional setup"})

        tokens = auth_result["AuthenticationResult"]
        id_token = tokens["IdToken"]

        user_info = cognito.admin_get_user(
            UserPoolId=USER_POOL_ID, Username=email
        )
        attrs = {a["Name"]: a["Value"] for a in user_info.get("UserAttributes", [])}

        return _response(200, {
            "token": id_token,
            "user_id": attrs.get("sub", ""),
            "email": email,
            "role": attrs.get("custom:role", "operator"),
        })

    except cognito.exceptions.NotAuthorizedException:
        return _response(401, {"error": "Invalid email or password"})
    except cognito.exceptions.UserNotFoundException:
        return _response(401, {"error": "Invalid email or password"})
    except Exception:
        logger.exception("Auth handler error")
        return _response(500, {"error": "Internal server error"})


def _is_websocket_ticket_request(event) -> bool:
    path = event.get("resource") or event.get("path") or ""
    return path.endswith("/auth/websocket-ticket")


def _create_websocket_ticket(event):
    claims = (
        event.get("requestContext", {})
        .get("authorizer", {})
        .get("claims", {})
    )
    user_id = claims.get("sub")
    if not user_id:
        return _response(401, {"error": "Authentication required"})

    ticket = websocket_ticket_repository.create_ticket(
        user_id=user_id,
        role=claims.get("custom:role", "operator"),
    )
    return _response(200, ticket)


def _response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": response_headers(),
        "body": json.dumps(body, default=str),
    }
