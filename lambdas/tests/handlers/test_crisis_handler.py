import json
from unittest.mock import patch

from handlers import crisis_handler


@patch("handlers.crisis_handler.crisis_response_service.handle_crisis_detection")
def test_step_functions_payload_returns_service_result(mock_handle):
    mock_handle.return_value = {"case_id": "CASE-1", "queue_id": "Q-1"}

    result = crisis_handler.lambda_handler(
        {
            "case_id": "CASE-1",
            "user_id": "USER-1",
            "crisis_type": "self_harm",
            "is_victim": False,
        },
        None,
    )

    assert result == {"case_id": "CASE-1", "queue_id": "Q-1"}
    mock_handle.assert_called_once_with(
        case_id="CASE-1",
        user_id="USER-1",
        crisis_type="self_harm",
        is_victim=False,
    )


@patch("handlers.crisis_handler.crisis_response_service.handle_crisis_detection")
def test_api_gateway_payload_returns_http_response(mock_handle):
    mock_handle.return_value = {"case_id": "CASE-2", "queue_id": "Q-2"}

    result = crisis_handler.lambda_handler(
        {
            "body": json.dumps(
                {
                    "case_id": "CASE-2",
                    "user_id": "USER-2",
                    "crisis_type": "self_harm",
                    "is_victim": True,
                }
            )
        },
        None,
    )

    assert result["statusCode"] == 200
    assert json.loads(result["body"])["queue_id"] == "Q-2"
    mock_handle.assert_called_once_with(
        case_id="CASE-2",
        user_id="USER-2",
        crisis_type="self_harm",
        is_victim=True,
    )


def test_step_functions_payload_raises_for_invalid_contract():
    try:
        crisis_handler.lambda_handler(
            {"case_id": "CASE-3", "user_id": "USER-3"},
            None,
        )
    except ValueError as error:
        assert str(error) == "crisis_type is required"
    else:
        raise AssertionError("workflow invocation must fail on an invalid payload")
