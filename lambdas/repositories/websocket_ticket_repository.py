import secrets
import time

from boto3.dynamodb.conditions import Attr

from .base import get_table


TICKET_TTL_SECONDS = 60
MAX_CREATE_ATTEMPTS = 3


def _table():
    return get_table("WEBSOCKET_TICKETS_TABLE")


def create_ticket(user_id: str, role: str) -> dict[str, str | int]:
    table = _table()
    expires_at = int(time.time()) + TICKET_TTL_SECONDS

    for _ in range(MAX_CREATE_ATTEMPTS):
        ticket = secrets.token_urlsafe(32)
        try:
            table.put_item(
                Item={
                    "ticket": ticket,
                    "user_id": user_id,
                    "role": role,
                    "ttl": expires_at,
                },
                ConditionExpression=Attr("ticket").not_exists(),
            )
            return {"ticket": ticket, "expires_at": expires_at}
        except table.meta.client.exceptions.ConditionalCheckFailedException:
            continue

    raise RuntimeError("Unable to create a unique WebSocket ticket")


def consume_ticket(ticket: str) -> dict | None:
    response = _table().delete_item(
        Key={"ticket": ticket},
        ReturnValues="ALL_OLD",
    )
    item = response.get("Attributes")
    if not item or int(item.get("ttl", 0)) < int(time.time()):
        return None
    return item
