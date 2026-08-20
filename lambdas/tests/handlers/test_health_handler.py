import json
from unittest.mock import patch

from handlers.health_handler import lambda_handler


@patch("handlers.health_handler.rate_limiter_service")
@patch("handlers.health_handler.case_repository")
def test_health_is_ready_when_redis_is_disabled(
    mock_case_repository,
    mock_rate_limiter,
    monkeypatch,
):
    monkeypatch.setenv("USE_REDIS", "false")
    mock_case_repository.get_case.return_value = None

    result = lambda_handler({}, None)

    assert result["statusCode"] == 200
    body = json.loads(result["body"])
    assert body["status"] == "healthy"
    assert body["components"]["dynamodb"]["status"] == "healthy"
    assert body["components"]["redis"] == {"status": "disabled"}
    mock_rate_limiter._get_redis.assert_not_called()


@patch("handlers.health_handler.rate_limiter_service")
@patch("handlers.health_handler.case_repository")
def test_health_is_ready_when_redis_is_healthy(
    mock_case_repository,
    mock_rate_limiter,
    monkeypatch,
):
    monkeypatch.setenv("USE_REDIS", "true")
    mock_case_repository.get_case.return_value = None
    mock_rate_limiter._get_redis.return_value.ping.return_value = True

    result = lambda_handler({}, None)

    assert result["statusCode"] == 200
    body = json.loads(result["body"])
    assert body["status"] == "healthy"
    assert body["components"]["redis"]["status"] == "healthy"


@patch("handlers.health_handler.rate_limiter_service")
@patch("handlers.health_handler.case_repository")
def test_health_is_degraded_when_redis_is_unavailable(
    mock_case_repository,
    mock_rate_limiter,
    monkeypatch,
):
    monkeypatch.setenv("USE_REDIS", "true")
    mock_case_repository.get_case.return_value = None
    mock_rate_limiter._get_redis.return_value.ping.side_effect = RuntimeError(
        "connection refused"
    )

    result = lambda_handler({}, None)

    assert result["statusCode"] == 503
    body = json.loads(result["body"])
    assert body["status"] == "degraded"
    assert body["components"]["redis"]["status"] == "unhealthy"
    assert "error" not in body["components"]["redis"]


@patch("handlers.health_handler.rate_limiter_service")
@patch("handlers.health_handler.case_repository")
def test_health_does_not_expose_dynamodb_error_details(
    mock_case_repository,
    mock_rate_limiter,
    monkeypatch,
):
    monkeypatch.setenv("USE_REDIS", "false")
    mock_case_repository.get_case.side_effect = RuntimeError(
        "table tg-cases-private-account-detail is unavailable"
    )

    result = lambda_handler({}, None)

    assert result["statusCode"] == 503
    body = json.loads(result["body"])
    assert body["components"]["dynamodb"]["status"] == "unhealthy"
    assert "error" not in body["components"]["dynamodb"]


@patch("handlers.health_handler.rate_limiter_service")
@patch("handlers.health_handler.case_repository")
def test_production_health_omits_component_details(
    mock_case_repository,
    mock_rate_limiter,
    monkeypatch,
):
    monkeypatch.setenv("ENVIRONMENT", "prod")
    monkeypatch.setenv("USE_REDIS", "false")
    mock_case_repository.get_case.return_value = None

    result = lambda_handler({}, None)

    assert result["statusCode"] == 200
    body = json.loads(result["body"])
    assert body["status"] == "healthy"
    assert "components" not in body
    mock_rate_limiter._get_redis.assert_not_called()
    assert "private-account-detail" not in result["body"]
    mock_rate_limiter._get_redis.assert_not_called()
