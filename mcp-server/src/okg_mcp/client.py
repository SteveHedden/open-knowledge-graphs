"""HTTP client for the Open Knowledge Graphs API."""

from typing import Any

import httpx

BASE_URL = "https://api.openknowledgegraphs.com"
TIMEOUT = 30.0


async def api_get(path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    """Make a GET request to the OKG API.

    Args:
        path: API path (e.g., "/search", "/ontologies").
        params: Query parameters. None values are stripped.

    Returns:
        Parsed JSON response.

    Raises:
        httpx.HTTPStatusError: On non-2xx responses.
        httpx.TimeoutException: On request timeout.
    """
    clean_params = {k: v for k, v in (params or {}).items() if v is not None}
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        response = await client.get(f"{BASE_URL}{path}", params=clean_params)
        response.raise_for_status()
        return response.json()


def handle_api_error(e: Exception) -> str:
    """Format API errors into actionable messages."""
    if isinstance(e, httpx.HTTPStatusError):
        status = e.response.status_code
        if status == 400:
            return "Error: Bad request. Check that the 'q' parameter is provided."
        if status == 429:
            return "Error: Rate limit exceeded. Please wait before making more requests."
        return f"Error: API request failed with status {status}."
    if isinstance(e, httpx.TimeoutException):
        return "Error: Request timed out after 30s. The API may be temporarily unavailable."
    return f"Error: {type(e).__name__}: {e}"
