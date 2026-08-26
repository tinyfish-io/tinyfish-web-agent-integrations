from __future__ import annotations

import pytest

from tinyfish_hermes.normalize import (
    TinyFishPayloadError,
    normalize_fetch_documents,
    normalize_search_response,
    parse_jsonish,
)


def test_parse_jsonish_decodes_json_strings() -> None:
    assert parse_jsonish('{"a": 1}') == {"a": 1}
    assert parse_jsonish("  ") == ""
    assert parse_jsonish("not json") == "not json"
    assert parse_jsonish({"a": 1}) == {"a": 1}


def test_normalize_search_rest_envelope() -> None:
    payload = {
        "data": {
            "web": [
                {
                    "title": "TinyFish",
                    "url": "https://www.tinyfish.ai/",
                    "description": "Search and fetch",
                    "position": 1,
                }
            ]
        }
    }

    assert normalize_search_response(payload, limit=5) == {
        "success": True,
        "data": {
            "web": [
                {
                    "title": "TinyFish",
                    "url": "https://www.tinyfish.ai/",
                    "description": "Search and fetch",
                    "position": 1,
                }
            ]
        },
    }


def test_normalize_search_results_fallback_shape() -> None:
    payload = {
        "query": "tinyfish",
        "results": [
            {
                "position": 1,
                "title": "TinyFish",
                "snippet": "Search and fetch",
                "url": "https://www.tinyfish.ai/",
            }
        ],
    }

    result = normalize_search_response(payload, limit=5)

    assert result["success"] is True
    assert result["data"]["web"] == [
        {
            "title": "TinyFish",
            "url": "https://www.tinyfish.ai/",
            "description": "Search and fetch",
            "position": 1,
        }
    ]


def test_normalize_search_applies_limit() -> None:
    payload = {
        "results": [
            {"title": f"Result {idx}", "url": f"https://example.com/{idx}"}
            for idx in range(10)
        ]
    }

    result = normalize_search_response(payload, limit=3)

    assert len(result["data"]["web"]) == 3


def test_normalize_search_raises_on_error_payload() -> None:
    with pytest.raises(TinyFishPayloadError, match="quota exceeded"):
        normalize_search_response({"error": "quota exceeded"})


def test_normalize_fetch_rest_shape() -> None:
    payload = {
        "results": [
            {
                "url": "https://docs.tinyfish.ai/",
                "final_url": "https://docs.tinyfish.ai/",
                "title": "TinyFish Docs",
                "text": "# TinyFish",
                "format": "markdown",
            }
        ],
        "errors": [],
    }

    docs = normalize_fetch_documents(
        payload, fallback_urls=["https://docs.tinyfish.ai/"]
    )

    assert docs[0]["title"] == "TinyFish Docs"
    assert docs[0]["content"] == "# TinyFish"
    assert docs[0]["raw_content"] == "# TinyFish"
    assert docs[0]["metadata"]["sourceURL"] == "https://docs.tinyfish.ai/"


def test_normalize_fetch_reports_per_url_errors() -> None:
    payload = {
        "results": [],
        "errors": [{"url": "https://example.com", "error": "blocked"}],
    }

    docs = normalize_fetch_documents(payload, fallback_urls=["https://example.com"])

    assert docs == [
        {
            "url": "https://example.com",
            "title": "",
            "content": "",
            "raw_content": "",
            "error": "blocked",
            "metadata": {"sourceURL": "https://example.com"},
        }
    ]


def test_normalize_fetch_empty_payload_reports_fallback_urls() -> None:
    docs = normalize_fetch_documents({}, fallback_urls=["https://example.com"])

    assert docs[0]["url"] == "https://example.com"
    assert docs[0]["error"] == "TinyFish returned no content"


def test_normalize_fetch_string_documents_use_fallback_urls() -> None:
    docs = normalize_fetch_documents(
        {"results": ["plain text"]}, fallback_urls=["https://example.com"]
    )

    assert docs == [
        {
            "url": "https://example.com",
            "title": "",
            "content": "plain text",
            "raw_content": "plain text",
            "metadata": {"sourceURL": "https://example.com"},
        }
    ]


def test_normalize_fetch_raises_on_error_payload() -> None:
    with pytest.raises(TinyFishPayloadError, match="invalid key"):
        normalize_fetch_documents({"error": "invalid key"})
