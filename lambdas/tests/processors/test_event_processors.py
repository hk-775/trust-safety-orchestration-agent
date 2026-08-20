import json
from decimal import Decimal
from unittest.mock import MagicMock, patch

from processors import behavioral_processor, bulk_detector


@patch("processors.behavioral_processor.boto3.client")
def test_behavioral_processor_starts_configured_investigation(mock_client, monkeypatch):
    state_machine_arn = "arn:aws:states:us-east-1:123456789012:stateMachine:investigation"
    monkeypatch.setattr(
        behavioral_processor,
        "INVESTIGATION_STATE_MACHINE_ARN",
        state_machine_arn,
    )

    behavioral_processor._start_investigation("CASE-1", "user-1")

    request = mock_client.return_value.start_execution.call_args.kwargs
    assert request["stateMachineArn"] == state_machine_arn
    assert json.loads(request["input"])["case_id"] == "CASE-1"


@patch("processors.behavioral_processor.base.get_dynamodb_resource")
def test_behavioral_processor_serializes_anomaly_floats(mock_resource):
    table = MagicMock()
    mock_resource.return_value.Table.return_value = table

    behavioral_processor._update_anomaly_scores(
        "user-1",
        {
            "anomaly_score": 0.75,
            "account_tier": "new",
            "factors": [{"factor": "velocity", "contribution": 0.25}],
        },
    )

    item = table.put_item.call_args.kwargs["Item"]
    assert item["anomaly_score"] == Decimal("0.75")
    assert item["factors"][0]["contribution"] == Decimal("0.25")


@patch("processors.bulk_detector.boto3.client")
def test_bulk_detector_starts_configured_workflow(mock_client, monkeypatch):
    state_machine_arn = "arn:aws:states:us-east-1:123456789012:stateMachine:bulk"
    monkeypatch.setattr(
        bulk_detector,
        "BULK_ACTION_STATE_MACHINE_ARN",
        state_machine_arn,
    )

    bulk_detector._start_bulk_action("CASE-2", "192.0.2.0/24", 75)

    request = mock_client.return_value.start_execution.call_args.kwargs
    assert request["stateMachineArn"] == state_machine_arn
    workflow_input = json.loads(request["input"])
    assert workflow_input["profile_count"] == 75
    assert workflow_input["user_id"] == "bulk-192.0.2.0/24"
    assert workflow_input["user_ids"] == []
    assert workflow_input["confidence_score"] == 0.0
    assert workflow_input["action"] == "rate_limit"
    assert workflow_input["violation_type"] == "bot_farm"
