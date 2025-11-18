"""Tests for the Bato parser plugin."""

from __future__ import annotations

import json
from typing import Any

from bs4 import BeautifulSoup

from plugins.bato_parser import BatoParser


def test_parse_modern_script_payload() -> None:
    """BatoParser extracts images from modern script payloads."""

    html = """
    <html>
        <head>
            <script>
                const your_email = "";
                const imgHttps = [
                    "https://example.com/001.webp",
                    "https://example.com/002.webp"
                ];
                const local_text_sub = 'OMORI [Official]';
                const local_text_epi = 'Ch.11';
            </script>
        </head>
    </html>
    """

    soup = BeautifulSoup(html, "html.parser")
    parser = BatoParser()

    result = parser.parse(soup, "https://bato.to/chapter/3850217")

    assert result is not None
    assert result["image_urls"] == [
        "https://example.com/001.webp",
        "https://example.com/002.webp",
    ]
    assert result["title"] == "OMORI [Official]"
    assert result["chapter"] == "Ch.11"


def test_parse_qwik_payload_with_token_resolution() -> None:
    """BatoParser decodes qwik/json payloads with token indirection."""

    payload = {
        "objs": [
            {"unused": True},
            {"chapterData": "2", "comicData": "3"},
            {"dname": "Ch 5", "title": "Chapter 5", "imageFile": "4"},
            {"name": "Series Name", "title": "Ignored Title"},
            {"urlList": ["https://example.com/1.jpg", "", "https://example.com/2.jpg"]},
        ]
    }
    html = f"""
    <html>
        <body>
            <script type="qwik/json">{json.dumps(payload)}</script>
        </body>
    </html>
    """

    soup = BeautifulSoup(html, "html.parser")
    parser = BatoParser()

    result = parser.parse(soup, "https://bato.to/chapter/3850217")

    assert result is not None
    assert result["title"] == "Series Name"
    assert result["chapter"] == "Ch 5"
    assert result["image_urls"] == [
        "https://example.com/1.jpg",
        "https://example.com/2.jpg",
    ]


def test_parse_qwik_payload_invalid_returns_none(caplog: Any) -> None:
    """Invalid qwik payload is ignored without raising."""

    html = """
    <html>
        <body>
            <script type="qwik/json">{"objs":"not-a-list"}</script>
        </body>
    </html>
    """

    soup = BeautifulSoup(html, "html.parser")
    parser = BatoParser()

    with caplog.at_level("DEBUG"):
        result = parser.parse(soup, "https://bato.to/chapter/invalid")

    assert result is None
