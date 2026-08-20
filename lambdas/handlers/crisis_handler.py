import json
import logging

from handlers.http_response import response_headers
from services import crisis_response_service

logger = logging.getLogger(__name__)


def lambda_handler(event, context):
    if "body" not in event:
        return _handle_crisis(event)

    try:
        return _response(200, _handle_crisis(json.loads(event.get("body") or "{}")))

    except ValueError as e:
        return _response(400, {"error": str(e)})
    except Exception:
        logger.exception("Handler error")
        return _response(500, {"error": "Internal server error"})


def _handle_crisis(payload):
    user_id = payload.get("user_id")
    crisis_type = payload.get("crisis_type")
    case_id = payload.get("case_id")

    if not user_id:
        raise ValueError("user_id is required")
    if not crisis_type:
        raise ValueError("crisis_type is required")
    if not case_id:
        raise ValueError("case_id is required")

    return crisis_response_service.handle_crisis_detection(
        case_id=case_id,
        user_id=user_id,
        crisis_type=crisis_type,
        is_victim=bool(payload.get("is_victim", False)),
    )


def _response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": response_headers(),
        "body": json.dumps(body, default=str),
    }
