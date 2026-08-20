import os
import threading
import time
from functools import lru_cache

import boto3
from botocore.config import Config


_CLIENT_CONFIG = Config(
    retries={"total_max_attempts": 2, "mode": "standard"},
    connect_timeout=2,
    read_timeout=3,
)
_SECRET_CACHE_TTL_SECONDS = 300
_SECRET_CACHE: dict[str, tuple[float, str]] = {}
_SECRET_CACHE_LOCK = threading.Lock()


@lru_cache(maxsize=1)
def _secrets_client():
    return boto3.client("secretsmanager", config=_CLIENT_CONFIG)


def _get_secret(secret_arn: str) -> str:
    now = time.monotonic()
    with _SECRET_CACHE_LOCK:
        cached = _SECRET_CACHE.get(secret_arn)
        if cached and cached[0] > now:
            return cached[1]

        response = _secrets_client().get_secret_value(SecretId=secret_arn)
        secret = response.get("SecretString")
        if not secret:
            raise RuntimeError("Integration credential must be stored as SecretString")
        _SECRET_CACHE[secret_arn] = (
            now + _SECRET_CACHE_TTL_SECONDS,
            secret,
        )
        return secret


def get_auth_headers(integration: str) -> dict[str, str]:
    prefix = integration.upper()
    mode = os.environ.get(f"{prefix}_AUTH_MODE", "none").lower()
    if mode == "none":
        return {}

    secret_arn = os.environ.get(f"{prefix}_AUTH_SECRET_ARN", "")
    if not secret_arn:
        raise RuntimeError(f"{prefix}_AUTH_SECRET_ARN is required for {mode} auth")

    credential = _get_secret(secret_arn)
    if mode == "api-key":
        return {"X-Api-Key": credential}
    if mode == "bearer":
        return {"Authorization": f"Bearer {credential}"}
    raise RuntimeError(f"Unsupported {prefix}_AUTH_MODE: {mode}")
