from unittest.mock import Mock

import pytest

from services import integration_auth


@pytest.fixture(autouse=True)
def clear_caches():
    integration_auth._SECRET_CACHE.clear()
    integration_auth._secrets_client.cache_clear()
    yield
    integration_auth._SECRET_CACHE.clear()
    integration_auth._secrets_client.cache_clear()


def test_none_mode_does_not_call_secrets_manager(monkeypatch):
    monkeypatch.setenv("PLATFORM_AUTH_MODE", "none")
    client = Mock()
    monkeypatch.setattr(integration_auth, "_secrets_client", lambda: client)

    assert integration_auth.get_auth_headers("platform") == {}
    client.get_secret_value.assert_not_called()


@pytest.mark.parametrize(
    ("mode", "expected"),
    [
        ("api-key", {"X-Api-Key": "credential"}),
        ("bearer", {"Authorization": "Bearer credential"}),
    ],
)
def test_secret_backed_modes_return_expected_header(monkeypatch, mode, expected):
    monkeypatch.setenv("PLATFORM_AUTH_MODE", mode)
    monkeypatch.setenv(
        "PLATFORM_AUTH_SECRET_ARN",
        "arn:aws:secretsmanager:us-east-1:123456789012:secret:platform",
    )
    client = Mock()
    client.get_secret_value.return_value = {"SecretString": "credential"}
    monkeypatch.setattr(integration_auth, "_secrets_client", lambda: client)

    assert integration_auth.get_auth_headers("platform") == expected
    client.get_secret_value.assert_called_once_with(
        SecretId="arn:aws:secretsmanager:us-east-1:123456789012:secret:platform"
    )


def test_authenticated_mode_requires_secret_arn(monkeypatch):
    monkeypatch.setenv("PARTNER_INTEL_AUTH_MODE", "bearer")
    monkeypatch.delenv("PARTNER_INTEL_AUTH_SECRET_ARN", raising=False)

    with pytest.raises(RuntimeError, match="PARTNER_INTEL_AUTH_SECRET_ARN"):
        integration_auth.get_auth_headers("partner_intel")


def test_rejects_binary_secrets(monkeypatch):
    monkeypatch.setenv("PLATFORM_AUTH_MODE", "api-key")
    monkeypatch.setenv("PLATFORM_AUTH_SECRET_ARN", "secret-arn")
    client = Mock()
    client.get_secret_value.return_value = {"SecretBinary": b"credential"}
    monkeypatch.setattr(integration_auth, "_secrets_client", lambda: client)

    with pytest.raises(RuntimeError, match="SecretString"):
        integration_auth.get_auth_headers("platform")


def test_cached_secret_refreshes_after_ttl(monkeypatch):
    monkeypatch.setenv("PLATFORM_AUTH_MODE", "api-key")
    monkeypatch.setenv("PLATFORM_AUTH_SECRET_ARN", "secret-arn")
    client = Mock()
    client.get_secret_value.side_effect = [
        {"SecretString": "first"},
        {"SecretString": "rotated"},
    ]
    monkeypatch.setattr(integration_auth, "_secrets_client", lambda: client)
    clock = iter([1000.0, 1001.0, 1301.0])
    monkeypatch.setattr(integration_auth.time, "monotonic", lambda: next(clock))

    assert integration_auth.get_auth_headers("platform") == {"X-Api-Key": "first"}
    assert integration_auth.get_auth_headers("platform") == {"X-Api-Key": "first"}
    assert integration_auth.get_auth_headers("platform") == {"X-Api-Key": "rotated"}
    assert client.get_secret_value.call_count == 2
