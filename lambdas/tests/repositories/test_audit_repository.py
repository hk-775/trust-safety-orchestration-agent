from decimal import Decimal
from unittest.mock import MagicMock, patch

from repositories import audit_repository


@patch("repositories.audit_repository._table")
def test_write_log_converts_floats_recursively(mock_table):
    table = MagicMock()
    mock_table.return_value = table

    audit_repository.write_log(
        event_type="escalation",
        action="escalate_to_human_review",
        confidence_score=0.25,
        previous_value={
            "score": 0.1,
            "nested": [0.2, {"value": 0.3}],
        },
    )

    item = table.put_item.call_args.kwargs["Item"]
    assert item["confidence_score"] == Decimal("0.25")
    assert item["previous_value"] == {
        "score": Decimal("0.1"),
        "nested": [Decimal("0.2"), {"value": Decimal("0.3")}],
    }
