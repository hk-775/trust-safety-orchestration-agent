from decimal import Decimal

from repositories.base import to_dynamodb_types


def test_to_dynamodb_types_converts_nested_floats():
    assert to_dynamodb_types({
        "score": 0.75,
        "factors": [0.1, {"weight": 0.2}],
    }) == {
        "score": Decimal("0.75"),
        "factors": [Decimal("0.1"), {"weight": Decimal("0.2")}],
    }
