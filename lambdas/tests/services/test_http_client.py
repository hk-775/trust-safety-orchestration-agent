import pytest

from services.http_client import build_https_url


def test_build_https_url_encodes_path_and_query_values():
    result = build_https_url(
        "https://api.example.test/v1/users",
        "user/with space",
        "messages",
        query={"days": "30", "cursor": "a+b"},
    )

    assert result == (
        "https://api.example.test/v1/users/user%2Fwith%20space/messages"
        "?days=30&cursor=a%2Bb"
    )


@pytest.mark.parametrize(
    "url",
    [
        "",
        "http://api.example.test",
        "file:///etc/passwd",
        "https://user:password@api.example.test",
        "https://api.example.test?redirect=https://example.test",
        "https://api.example.test#fragment",
    ],
)
def test_build_https_url_rejects_unsafe_base_urls(url):
    with pytest.raises(ValueError, match="External API"):
        build_https_url(url, "resource")
