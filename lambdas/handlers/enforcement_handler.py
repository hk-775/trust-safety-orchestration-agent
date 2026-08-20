import json
import logging

from handlers.http_response import response_headers
from services import enforcement_engine_service

logger = logging.getLogger(__name__)


def lambda_handler(event, context):
    try:
        path = event.get("resource", event.get("path", ""))

        if event.get("is_bulk") or "bulk" in path:
            return _execute_bulk(event)
        else:
            return _execute_single(event)
    except json.JSONDecodeError:
        return _response(400, {"error": "Invalid JSON body"})
    except ValueError as e:
        return _response(400, {"error": str(e)})
    except Exception:
        logger.exception("Enforcement handler error")
        return _response(500, {"error": "Internal server error"})


def _body(event):
    body = event.get("body")
    if body is None:
        return event
    if isinstance(body, str):
        return json.loads(body or "{}")
    return body


def _execute_single(event):
    body = _body(event)

    required = ["case_id", "action", "violation_type", "confidence_score"]
    missing = [f for f in required if f not in body]
    if missing:
        return _response(400, {"error": f"Missing required fields: {missing}"})

    result = enforcement_engine_service.execute_action(
        case_id=body["case_id"],
        user_id=body.get("user_id", ""),
        action=body["action"],
        violation_type=body["violation_type"],
        confidence_score=float(body["confidence_score"]),
        is_autonomous=body.get("is_autonomous", False),
        reviewer_id=body.get("reviewer_id"),
        duration_hours=body.get("duration_hours"),
    )

    return _response(200, result)


def _execute_bulk(event):
    body = _body(event)

    required = ["case_id", "user_ids", "action", "violation_type"]
    missing = [f for f in required if f not in body]
    if missing:
        return _response(400, {"error": f"Missing required fields: {missing}"})

    user_ids = body["user_ids"]
    if len(user_ids) > 500:
        return _response(400, {"error": "Maximum 500 user_ids per bulk action"})

    result = enforcement_engine_service.execute_bulk_action(
        case_id=body["case_id"],
        user_ids=user_ids,
        action=body["action"],
        violation_type=body["violation_type"],
        attack_pattern=body.get("attack_pattern"),
    )

    return _response(200, result)


def _response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": response_headers(),
        "body": json.dumps(body, default=str),
    }
