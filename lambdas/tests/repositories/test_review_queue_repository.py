from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from repositories import review_queue_repository


class ConditionalCheckFailedException(Exception):
    pass


@patch("repositories.review_queue_repository._table")
def test_dedupe_key_reuses_queue_item_on_retry(mock_table):
    table = MagicMock()
    table.meta = SimpleNamespace(
        client=SimpleNamespace(
            exceptions=SimpleNamespace(
                ConditionalCheckFailedException=ConditionalCheckFailedException
            )
        )
    )
    table.put_item.side_effect = [None, ConditionalCheckFailedException()]
    mock_table.return_value = table

    first_queue_id = review_queue_repository.add_to_queue(
        case_id="CASE-001",
        priority="medium",
        escalation_reason="no_confidence_scores",
        dedupe_key="escalation:CASE-001:no_confidence_scores",
    )
    retry_queue_id = review_queue_repository.add_to_queue(
        case_id="CASE-001",
        priority="medium",
        escalation_reason="no_confidence_scores",
        dedupe_key="escalation:CASE-001:no_confidence_scores",
    )

    assert first_queue_id == retry_queue_id
    assert first_queue_id.startswith("Q-")
    assert table.put_item.call_count == 2
    assert "ConditionExpression" in table.put_item.call_args.kwargs
