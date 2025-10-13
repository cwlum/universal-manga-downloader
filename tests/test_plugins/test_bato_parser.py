"""Tests for the Bato parser plugin."""

from __future__ import annotations

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
    assert result["title"] == "OMORI__Official"
    assert result["chapter"] == "Ch.11"
