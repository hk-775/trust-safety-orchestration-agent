import json
from pathlib import Path


def _bulk_workflow():
    workflow_path = (
        Path(__file__).parents[2]
        / "statemachines"
        / "bulk_action_workflow.asl.json"
    )
    return json.loads(workflow_path.read_text())


def _investigation_workflow():
    workflow_path = (
        Path(__file__).parents[2]
        / "statemachines"
        / "investigation_workflow.asl.json"
    )
    return json.loads(workflow_path.read_text())


def test_bulk_workflow_requires_users_before_autonomous_enforcement():
    choice = _bulk_workflow()["States"]["ValidateConfidence"]["Choices"][0]
    requirements = choice["And"]

    assert {
        condition["Variable"]
        for condition in requirements
    } == {"$.confidence_score", "$.user_ids[0]"}
    assert any(condition.get("IsPresent") is True for condition in requirements)


def test_bulk_escalation_payload_matches_handler_contract():
    parameters = _bulk_workflow()["States"]["EscalateToHumanReview"]["Parameters"]

    assert parameters["user_id.$"] == "$.user_id"
    assert "user_ids.$" not in parameters
    assert parameters["confidence"]["primary_violation"] == "bot_farm"
    assert parameters["confidence"]["primary_score.$"] == "$.confidence_score"


def test_crisis_task_matches_handler_and_does_not_duplicate_escalation():
    task = _investigation_workflow()["States"]["HandleCrisis"]

    assert task["Parameters"] == {
        "case_id.$": "$.case_id",
        "user_id.$": "$.user_id",
        "crisis_type.$": "$.evidence.sensitive_category",
        "is_victim": False,
    }
    assert task["Next"] == "InvestigationComplete"
    assert task["Catch"][0]["Next"] == "EscalateOnError"
