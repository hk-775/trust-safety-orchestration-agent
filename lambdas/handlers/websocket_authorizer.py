import logging

from repositories import websocket_ticket_repository


logger = logging.getLogger(__name__)


def lambda_handler(event, context):
    method_arn = event.get("methodArn") or event.get("routeArn", "*")
    ticket = (event.get("queryStringParameters") or {}).get("ticket", "")
    identity = websocket_ticket_repository.consume_ticket(ticket) if ticket else None

    if not identity:
        logger.warning("WebSocket authorization denied")
        return _policy("anonymous", "Deny", method_arn)

    return _policy(
        identity["user_id"],
        "Allow",
        method_arn,
        context={
            "user_id": identity["user_id"],
            "role": identity.get("role", "operator"),
        },
    )


def _policy(principal_id: str, effect: str, resource: str, context=None) -> dict:
    result = {
        "principalId": principal_id,
        "policyDocument": {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Action": "execute-api:Invoke",
                    "Effect": effect,
                    "Resource": resource,
                }
            ],
        },
    }
    if context:
        result["context"] = context
    return result
