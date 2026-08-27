"""Normalize TinyFish REST payloads into Hermes web-provider shapes."""

from __future__ import annotations

import json
from typing import Any


def _document_text(value: Any) -> str:
    # With format=json the Fetch API returns a document tree, not a string.
    if isinstance(value, str):
        return value
    if value is None:
        return ""
    try:
        return json.dumps(value, separators=(",", ":"))
    except (TypeError, ValueError):
        return str(value)


def normalize_search_response(payload: Any, limit: int = 5) -> dict[str, Any]:
    """Return Hermes' standard web-search response envelope."""

    results = payload.get("results") if isinstance(payload, dict) else None
    if not isinstance(results, list):
        results = []

    count = max(1, int(limit or 5))
    web_results: list[dict[str, Any]] = []
    for idx, item in enumerate(results[:count]):
        if not isinstance(item, dict):
            continue
        url = str(item.get("url") or "")
        web_results.append(
            {
                "title": str(item.get("title") or item.get("site_name") or url),
                "url": url,
                "description": str(item.get("snippet") or ""),
                "position": int(item.get("position") or idx + 1),
            }
        )
    return {"success": True, "data": {"web": web_results}}


def normalize_fetch_documents(
    payload: Any, fallback_urls: list[str] | None = None
) -> list[dict[str, Any]]:
    """Return Hermes' standard extract document list."""

    urls = list(fallback_urls or [])
    results = payload.get("results") if isinstance(payload, dict) else None
    errors = payload.get("errors") if isinstance(payload, dict) else None
    if not isinstance(results, list):
        results = []
    if not isinstance(errors, list):
        errors = []

    documents: list[dict[str, Any]] = []
    for idx, item in enumerate(results):
        if not isinstance(item, dict):
            continue
        url = str(
            item.get("url")
            or item.get("final_url")
            or (urls[idx] if idx < len(urls) else "")
        )
        raw = _document_text(item.get("text"))
        documents.append(
            {
                "url": url,
                "title": str(item.get("title") or ""),
                "content": raw,
                "raw_content": raw,
                "metadata": {
                    "sourceURL": url,
                    "finalURL": str(item.get("final_url") or url),
                    "description": str(item.get("description") or ""),
                    "language": str(item.get("language") or ""),
                },
            }
        )

    for idx, item in enumerate(errors):
        if not isinstance(item, dict):
            continue
        url = str(item.get("url") or (urls[idx] if idx < len(urls) else ""))
        documents.append(
            {
                "url": url,
                "title": "",
                "content": "",
                "raw_content": "",
                "error": str(item.get("error") or "fetch failed"),
                "metadata": {"sourceURL": url},
            }
        )

    if not documents and urls:
        return [
            {
                "url": url,
                "title": "",
                "content": "",
                "raw_content": "",
                "error": "TinyFish returned no content",
                "metadata": {"sourceURL": url},
            }
            for url in urls
        ]
    return documents
