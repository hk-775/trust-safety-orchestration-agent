"""Helpers for constructing outbound integration URLs safely."""

from collections.abc import Mapping
from urllib.parse import quote, urlencode, urlsplit, urlunsplit


def build_https_url(
    base_url: str,
    *path_segments: str,
    query: Mapping[str, str] | None = None,
) -> str:
    """Build an HTTPS URL from a configured base URL and untrusted values."""
    try:
        parsed = urlsplit(base_url)
        port = parsed.port
    except ValueError as error:
        raise ValueError("External API URL is invalid") from error

    if (
        parsed.scheme.lower() != "https"
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError(
            "External API base URL must be HTTPS and cannot contain credentials, "
            "a query string, or a fragment"
        )

    hostname = parsed.hostname.encode("idna").decode("ascii")
    netloc = f"[{hostname}]" if ":" in hostname else hostname
    if port is not None:
        netloc = f"{netloc}:{port}"

    path = parsed.path.rstrip("/")
    if path_segments:
        encoded_segments = "/".join(quote(str(segment), safe="") for segment in path_segments)
        path = f"{path}/{encoded_segments}" if path else f"/{encoded_segments}"

    query_string = urlencode(query or {})
    return urlunsplit(("https", netloc, path or "/", query_string, ""))
