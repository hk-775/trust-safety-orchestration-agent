import json
import logging
import os
import urllib.request

from repositories import audit_repository
from services.http_client import build_https_url

logger = logging.getLogger(__name__)

SUPPORTED_NOTIFICATION_TYPES = {
    "appeal_acknowledgment",
    "crisis_resources",
    "enforcement",
}
SUPPORTED_CHANNELS = {"email", "in_app"}


def lambda_handler(event, context):
    logger.info("Notification processor invoked", extra={"record_count": len(event.get("Records", []))})

    batch_item_failures = []

    for record in event.get("Records", []):
        try:
            _process_record(record)
        except Exception as e:
            logger.error(
                "Failed to process notification record",
                extra={
                    "error_type": type(e).__name__,
                    "message_id": record.get("messageId"),
                },
            )
            batch_item_failures.append({
                "itemIdentifier": record["messageId"],
            })

    return {"batchItemFailures": batch_item_failures}


def _process_record(record):
    body = json.loads(record["body"])
    user_id = body["user_id"]
    notification_type = body["notification_type"]
    channel = body["channel"]
    if notification_type not in SUPPORTED_NOTIFICATION_TYPES:
        raise ValueError(f"Unsupported notification type: {notification_type}")
    if channel not in SUPPORTED_CHANNELS:
        raise ValueError(f"Unsupported notification channel: {channel}")
    if not body.get("notification_id"):
        raise ValueError("Notification ID is required")
    if not body.get("subject") or not body.get("body"):
        raise ValueError("Notification subject and body are required")

    logger.info(
        "Processing notification",
        extra={
            "notification_type": notification_type,
            "channel": channel,
        },
    )

    result = _deliver_to_platform(body)

    audit_repository.write_log(
        event_type="notification_delivered",
        action=f"deliver_{notification_type}",
        user_id=user_id,
        reasoning=(
            f"Notification type={notification_type} delivered through "
            f"channel={channel}, status={result['status']}"
        ),
    )

    logger.info(
        "Notification delivered",
        extra={
            "notification_type": notification_type,
            "channel": channel,
            "status": result["status"],
        },
    )


def _deliver_to_platform(message: dict) -> dict:
    base_url = os.environ.get("PLATFORM_USER_API_URL", "")
    if not base_url:
        raise RuntimeError("PLATFORM_USER_API_URL is required for notification delivery")

    user_id = str(message["user_id"])
    url = build_https_url(base_url, user_id, "notifications")
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Idempotency-Key": str(message["notification_id"]),
    }
    api_key = os.environ.get("PLATFORM_API_KEY")
    if api_key:
        headers["X-Api-Key"] = api_key
    request = urllib.request.Request(
        url,
        data=json.dumps(message, default=str).encode(),
        headers=headers,
        method="POST",
    )

    # build_https_url rejects non-HTTPS schemes before this request.
    with urllib.request.urlopen(request, timeout=15) as response:  # nosec B310
        return {"status": response.status}
