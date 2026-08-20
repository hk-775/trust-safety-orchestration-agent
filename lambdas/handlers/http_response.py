"""Shared HTTP response headers for API Gateway handlers."""

import os


def response_headers(content_type: str = "application/json") -> dict[str, str]:
    return {
        "Content-Type": content_type,
        "Access-Control-Allow-Origin": os.environ.get(
            "ALLOWED_CORS_ORIGIN",
            "http://localhost:3000",
        ),
        "Vary": "Origin",
    }
