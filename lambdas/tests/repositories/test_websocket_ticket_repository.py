from types import SimpleNamespace
from unittest.mock import Mock

from repositories import websocket_ticket_repository as repository


class ConditionalCheckFailedException(Exception):
    pass


def _table():
    table = Mock()
    table.meta.client.exceptions = SimpleNamespace(
        ConditionalCheckFailedException=ConditionalCheckFailedException
    )
    return table


def test_create_ticket_stores_short_lived_identity(monkeypatch):
    table = _table()
    monkeypatch.setattr(repository, "_table", lambda: table)
    monkeypatch.setattr(repository.time, "time", lambda: 1000)
    monkeypatch.setattr(repository.secrets, "token_urlsafe", lambda _: "ticket-value")

    result = repository.create_ticket("user-123", "reviewer")

    assert result == {"ticket": "ticket-value", "expires_at": 1060}
    item = table.put_item.call_args.kwargs["Item"]
    assert item == {
        "ticket": "ticket-value",
        "user_id": "user-123",
        "role": "reviewer",
        "ttl": 1060,
    }


def test_create_ticket_retries_collision(monkeypatch):
    table = _table()
    table.put_item.side_effect = [ConditionalCheckFailedException(), None]
    values = iter(["collision", "unique"])
    monkeypatch.setattr(repository, "_table", lambda: table)
    monkeypatch.setattr(repository.time, "time", lambda: 1000)
    monkeypatch.setattr(repository.secrets, "token_urlsafe", lambda _: next(values))

    result = repository.create_ticket("user-123", "operator")

    assert result["ticket"] == "unique"
    assert table.put_item.call_count == 2


def test_consume_ticket_atomically_deletes_and_returns_identity(monkeypatch):
    table = _table()
    table.delete_item.return_value = {
        "Attributes": {
            "ticket": "ticket-value",
            "user_id": "user-123",
            "role": "admin",
            "ttl": 1060,
        }
    }
    monkeypatch.setattr(repository, "_table", lambda: table)
    monkeypatch.setattr(repository.time, "time", lambda: 1000)

    identity = repository.consume_ticket("ticket-value")

    assert identity["user_id"] == "user-123"
    table.delete_item.assert_called_once_with(
        Key={"ticket": "ticket-value"},
        ReturnValues="ALL_OLD",
    )


def test_consume_ticket_rejects_expired_ticket(monkeypatch):
    table = _table()
    table.delete_item.return_value = {
        "Attributes": {"ticket": "ticket-value", "ttl": 999}
    }
    monkeypatch.setattr(repository, "_table", lambda: table)
    monkeypatch.setattr(repository.time, "time", lambda: 1000)

    assert repository.consume_ticket("ticket-value") is None
