from __future__ import annotations

import json

from tinyfish_hermes.normalize import (
    normalize_fetch_documents,
    normalize_search_response,
)


def test_normalize_search_live_item_shape() -> None:
    # Pinned to the live Search API item keys: position, site_name, snippet, title, url.
    payload = {
        "query": "tinyfish",
        "total_results": 1,
        "page": 1,
        "results": [
            {
                "position": 1,
                "site_name": "TinyFish",
                "snippet": "Search and fetch",
                "title": "TinyFish Web Agent",
                "url": "https://www.tinyfish.ai/",
            }
        ],
    }

    assert normalize_search_response(payload, limit=5) == {
        "success": True,
        "data": {
            "web": [
                {
                    "title": "TinyFish Web Agent",
                    "url": "https://www.tinyfish.ai/",
                    "description": "Search and fetch",
                    "position": 1,
                }
            ]
        },
    }


def test_normalize_search_title_falls_back_to_site_name_then_url() -> None:
    payload = {
        "results": [
            {"site_name": "TinyFish", "url": "https://a.example", "snippet": ""},
            {"url": "https://b.example"},
        ]
    }

    web = normalize_search_response(payload, limit=5)["data"]["web"]

    assert web[0]["title"] == "TinyFish"
    assert web[1]["title"] == "https://b.example"
    assert web[1]["position"] == 2


def test_normalize_search_applies_limit() -> None:
    payload = {
        "results": [
            {"title": f"Result {idx}", "url": f"https://example.com/{idx}"}
            for idx in range(10)
        ]
    }

    result = normalize_search_response(payload, limit=3)

    assert len(result["data"]["web"]) == 3


def test_normalize_search_tolerates_malformed_payloads() -> None:
    assert normalize_search_response(None)["data"]["web"] == []
    assert normalize_search_response({"results": "nope"})["data"]["web"] == []
    assert normalize_search_response({"results": ["nope"]})["data"]["web"] == []


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


def test_normalize_fetch_json_format_serializes_document_tree() -> None:
    tree = {"type": "root", "children": [{"type": "heading", "text": "TinyFish"}]}
    payload = {"results": [{"url": "https://example.com", "text": tree}], "errors": []}

    docs = normalize_fetch_documents(payload)

    assert docs[0]["content"] == json.dumps(tree, separators=(",", ":"))
    assert docs[0]["raw_content"] == docs[0]["content"]


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


def test_normalize_fetch_tolerates_malformed_payloads() -> None:
    assert normalize_fetch_documents(None) == []
    assert normalize_fetch_documents({"results": "nope", "errors": "nope"}) == []
    assert normalize_fetch_documents({"results": ["nope"], "errors": [None]}) == []
