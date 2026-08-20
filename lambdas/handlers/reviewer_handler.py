import json
import logging

from handlers.http_response import response_headers
from repositories import reviewer_repository

logger = logging.getLogger(__name__)


def lambda_handler(event, context):
    try:
        path_params = event.get("pathParameters") or {}
        reviewer_id = path_params.get("reviewerId")

        if not reviewer_id:
            raise ValueError("reviewerId path parameter is required")

        metrics = reviewer_repository.get_exposure_metrics(reviewer_id)

        return _response(200, metrics)

    except ValueError as e:
        return _response(400, {"error": str(e)})
    except Exception:
        logger.exception("Handler error")
        return _response(500, {"error": "Internal server error"})


def _response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": response_headers(),
        "body": json.dumps(body, default=str),
    }
