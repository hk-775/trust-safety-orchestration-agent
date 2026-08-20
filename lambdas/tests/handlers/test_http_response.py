from handlers.http_response import response_headers


def test_response_headers_use_configured_cors_origin(monkeypatch):
    monkeypatch.setenv("ALLOWED_CORS_ORIGIN", "https://dashboard.example.test")

    headers = response_headers()

    assert headers == {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "https://dashboard.example.test",
        "Vary": "Origin",
    }
