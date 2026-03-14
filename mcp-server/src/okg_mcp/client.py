"""HTTP client for the Open Knowledge Graphs API.

Provides two parallel search paths:
1. Semantic search via the Vectorize-backed API
2. Text search over the static JSON datasets

Results are merged and deduplicated by wikidataId.
"""

import asyncio
from typing import Any

import httpx

BASE_URL = "https://api.openknowledgegraphs.com"
STATIC_URL = "https://openknowledgegraphs.com/data"
TIMEOUT = 30.0

# In-memory cache for static datasets (populated once per server lifetime)
_static_cache: dict[str, list[dict[str, Any]]] = {}


async def api_get(path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    """Make a GET request to the OKG semantic search API."""
    clean_params = {k: v for k, v in (params or {}).items() if v is not None}
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        response = await client.get(f"{BASE_URL}{path}", params=clean_params)
        response.raise_for_status()
        return response.json()


async def _fetch_static(dataset: str) -> list[dict[str, Any]]:
    """Fetch and cache a static JSON dataset."""
    if dataset in _static_cache:
        return _static_cache[dataset]
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        response = await client.get(f"{STATIC_URL}/{dataset}.json")
        response.raise_for_status()
        items = response.json().get("items", [])
        _static_cache[dataset] = items
        return items


def _text_match(item: dict[str, Any], terms: list[str], category: str | None) -> bool:
    """Check if an item matches all search terms."""
    if category and (item.get("category") or "").lower() != category.lower():
        return False
    text = " ".join(
        filter(None, [
            item.get("title", ""),
            item.get("description", ""),
            " ".join(item.get("types", [])),
            item.get("category", ""),
        ])
    ).lower()
    return all(t in text for t in terms)


async def text_search(
    q: str,
    datasets: list[str],
    category: str | None = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Search static JSON datasets by text matching."""
    all_items = await asyncio.gather(*[_fetch_static(ds) for ds in datasets])
    terms = q.lower().split()
    results = []
    for items in all_items:
        for item in items:
            if _text_match(item, terms, category):
                results.append({**item, "match": "text"})
    return results[:limit]


async def dual_search(
    path: str,
    params: dict[str, Any],
    datasets: list[str],
    category: str | None = None,
    limit: int = 20,
) -> dict[str, Any]:
    """Run semantic and text searches in parallel, merge and deduplicate."""
    semantic_task = api_get(path, params)
    text_task = text_search(params["q"], datasets, category, limit)

    semantic_data, text_results = await asyncio.gather(
        semantic_task, text_task, return_exceptions=True,
    )

    # Start with semantic results if available
    if isinstance(semantic_data, Exception):
        semantic_results = []
        query = params["q"]
    else:
        semantic_results = semantic_data.get("results", [])
        query = semantic_data.get("query", params["q"])

    # Collect text-only matches (not in semantic results)
    semantic_ids = {r.get("wikidataId") for r in semantic_results}
    text_only: list[dict[str, Any]] = []
    if not isinstance(text_results, Exception):
        for item in text_results:
            if item.get("wikidataId") not in semantic_ids:
                text_only.append(item)

    # Merge: text-only matches first (they were missed by the index),
    # then semantic results, then truncate to limit
    merged = [*text_only, *semantic_results]

    return {
        "query": query,
        "category": category,
        "total": len(merged[:limit]),
        "results": merged[:limit],
    }


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
