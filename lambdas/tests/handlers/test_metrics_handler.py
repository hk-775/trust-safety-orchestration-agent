import json
from unittest.mock import patch

from handlers.metrics_handler import lambda_handler


class TestRecentActions:

    @patch("repositories.audit_repository.query_by_event_type")
    def test_returns_enforcement_logs_with_frontend_id(
        self, mock_query, api_gateway_event, lambda_context
    ):
        mock_query.return_value = [
            {
                "audit_id": "AUDIT-01K2TQF3M8E1X9K7G6H5J4N3P2",
                "event_type": "enforcement",
                "action": "permanent_ban",
                "timestamp": "2026-08-19T18:00:00+00:00",
            }
        ]

        event = api_gateway_event(method="GET", path="/actions/recent")
        result = lambda_handler(event, lambda_context)

        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert body["recent_actions"] == [
            {
                "audit_id": "AUDIT-01K2TQF3M8E1X9K7G6H5J4N3P2",
                "log_id": "AUDIT-01K2TQF3M8E1X9K7G6H5J4N3P2",
                "event_type": "enforcement",
                "action": "permanent_ban",
                "timestamp": "2026-08-19T18:00:00+00:00",
            }
        ]
        mock_query.assert_called_once_with("enforcement", limit=20)
