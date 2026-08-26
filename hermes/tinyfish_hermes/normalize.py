"""Normalize TinyFish REST payloads into Hermes web-provider shapes."""

from __future__ import annotations

import json
from typing import Any


class TinyFishPayloadError(ValueError):
    """Raised when a TinyFish payload reports an error."""


def parse_jsonish(value: Any) -> Any:
    """Parse JSON strings when possible and return other values unchanged."""

    if isinstance(value, str):
        text = value.strip()
        if not text:
            return text
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return value
    return value


def _unwrap(raw: Any) -> Any:
    payload = parse_jsonish(raw)
    if isinstance(payload, dict) and payload.get("error"):
        raise TinyFishPayloadError(str(payload["error"]))
    return payload


def normalize_search_response(payload: Any, limit: int = 5) -> dict[str, Any]:
    """Return Hermes' standard web-search response envelope."""

    data = _unwrap(payload)
    if isinstance(data, list):
        results = data
    elif isinstance(data, dict):
        if isinstance(data.get("data"), dict) and isinstance(
            data["data"].get("web"), list
        ):
            return {
                "success": True,
                "data": {"web": data["data"]["web"][: max(1, int(limit or 5))]},
            }
        results = data.get("results") or data.get("web") or []
    else:
        results = []

    count = max(1, int(limit or 5))
    web_results: list[dict[str, Any]] = []
    for idx, item in enumerate(list(results)[:count]):
        if not isinstance(item, dict):
            continue
        url = str(item.get("url") or item.get("link") or "")
        web_results.append(
            {
                "title": str(item.get("title") or item.get("site_name") or url),
                "url": url,
                "description": str(
                    item.get("snippet")
                    or item.get("description")
                    or item.get("content")
                    or item.get("text")
                    or ""
                ),
                "position": int(item.get("position") or idx + 1),
            }
        )
    return {"success": True, "data": {"web": web_results}}


def normalize_fetch_documents(
    payload: Any, fallback_urls: list[str] | None = None
) -> list[dict[str, Any]]:
    """Return Hermes' standard extract document list."""

    urls = list(fallback_urls or [])
    data = _unwrap(payload)

    if isinstance(data, dict):
        results = data.get("results") or data.get("documents") or []
        errors = data.get("errors") or data.get("failed_results") or []
    elif isinstance(data, list):
        results = data
        errors = []
    else:
        results = []
        errors = []

    documents: list[dict[str, Any]] = []
    for idx, item in enumerate(list(results)):
        if isinstance(item, str):
            url = urls[idx] if idx < len(urls) else ""
            documents.append(
                {
                    "url": url,
                    "title": "",
                    "content": item,
                    "raw_content": item,
                    "metadata": {"sourceURL": url},
                }
            )
            continue
        if not isinstance(item, dict):
            continue
        url = str(
            item.get("url")
            or item.get("final_url")
            or (urls[idx] if idx < len(urls) else "")
        )
        raw = str(
            item.get("text")
            or item.get("markdown")
            or item.get("raw_content")
            or item.get("content")
            or ""
        )
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

    for idx, item in enumerate(list(errors)):
        if isinstance(item, dict):
            url = str(item.get("url") or (urls[idx] if idx < len(urls) else ""))
            error = str(item.get("error") or item.get("message") or "fetch failed")
        else:
            url = urls[idx] if idx < len(urls) else ""
            error = str(item)
        documents.append(
            {
                "url": url,
                "title": "",
                "content": "",
                "raw_content": "",
                "error": error,
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
