import json
import logging
import os
import time

from handlers.http_response import response_headers
from repositories import case_repository
from services import rate_limiter_service

logger = logging.getLogger(__name__)


def lambda_handler(event, context):
    try:
        components = {}

        # Check DynamoDB
        dynamo_start = time.time()
        try:
            case_repository.get_case("nonexistent")
            dynamo_latency_ms = round((time.time() - dynamo_start) * 1000, 2)
            components["dynamodb"] = {
                "status": "healthy",
                "latency_ms": dynamo_latency_ms,
            }
        except Exception as e:
            dynamo_latency_ms = round((time.time() - dynamo_start) * 1000, 2)
            logger.warning(
                "DynamoDB health check failed",
                extra={"error_type": type(e).__name__},
            )
            components["dynamodb"] = {
                "status": "unhealthy",
                "latency_ms": dynamo_latency_ms,
            }

        if os.environ.get("USE_REDIS", "false").lower() == "true":
            redis_start = time.time()
            try:
                rate_limiter_service._get_redis().ping()
                redis_latency_ms = round((time.time() - redis_start) * 1000, 2)
                components["redis"] = {
                    "status": "healthy",
                    "latency_ms": redis_latency_ms,
                }
            except Exception as e:
                redis_latency_ms = round((time.time() - redis_start) * 1000, 2)
                logger.warning(
                    "Redis health check failed",
                    extra={"error_type": type(e).__name__},
                )
                components["redis"] = {
                    "status": "unhealthy",
                    "latency_ms": redis_latency_ms,
                }
        else:
            components["redis"] = {"status": "disabled"}

        overall_healthy = all(
            component["status"] in {"healthy", "disabled"}
            for component in components.values()
        )

        result = {
            "status": "healthy" if overall_healthy else "degraded",
            "timestamp": time.time(),
            "components": components,
        }

        status_code = 200 if overall_healthy else 503
        return _response(status_code, result)

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
