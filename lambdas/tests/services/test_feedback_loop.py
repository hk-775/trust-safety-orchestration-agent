import json
from unittest.mock import MagicMock, patch

from services import feedback_loop_service


@patch("services.feedback_loop_service.get_bucket_name")
@patch("services.feedback_loop_service.get_s3_client")
def test_feedback_uses_configured_evidence_bucket(mock_get_client, mock_get_bucket):
    client = MagicMock()
    mock_get_client.return_value = client
    mock_get_bucket.return_value = "evidence-bucket"

    key = feedback_loop_service.record_decision_feedback(
        case_id="CASE-1",
        predicted_violation="scam",
        predicted_confidence=0.9,
        actual_decision="approve_action",
        reviewer_id="reviewer-1",
    )

    mock_get_bucket.assert_called_once_with("EVIDENCE_BUCKET")
    assert key.startswith("feedback/")
    call = client.put_object.call_args.kwargs
    assert call["Bucket"] == "evidence-bucket"
    assert call["Key"] == key
    assert json.loads(call["Body"])["case_id"] == "CASE-1"
