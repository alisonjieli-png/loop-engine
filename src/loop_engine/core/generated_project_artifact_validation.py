"""Deterministic format checks for generated project artifacts.

The checks inspect already produced bytes. They do not write files, execute a
project, call a provider, infer task completion, or broaden authority.
"""
from __future__ import annotations

import json
from html.parser import HTMLParser


class _HtmlDocumentParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.saw_html = False

    def handle_starttag(self, tag, attrs) -> None:
        del attrs
        if tag.lower() == "html":
            self.saw_html = True


def verify_artifact_content(media_type: str, content: bytes) -> tuple:
    """Return format validity, method, and a bounded failure description."""
    kind = media_type.lower().split(";", 1)[0].strip()
    if not content:
        return False, "nonempty", "artifact is empty"
    if kind == "application/pdf":
        valid = content.startswith(b"%PDF-") and b"%%EOF" in content[-4096:]
        return valid, "pdf_signature_and_eof", (
            "" if valid else "PDF signature or EOF marker is missing")
    if kind in ("text/html", "application/xhtml+xml"):
        try:
            text = content.decode("utf-8")
            parser = _HtmlDocumentParser()
            parser.feed(text)
            valid = parser.saw_html and "</html>" in text.lower()
        except (UnicodeDecodeError, ValueError) as exc:
            return False, "html_parse", type(exc).__name__
        return valid, "html_parse", "" if valid else "HTML root is missing"
    if kind == "application/json":
        try:
            json.loads(content.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            return False, "json_parse", type(exc).__name__
        return True, "json_parse", ""
    if kind.startswith("text/"):
        try:
            content.decode("utf-8")
        except UnicodeDecodeError as exc:
            return False, "utf8_decode", type(exc).__name__
        return True, "utf8_decode", ""
    signatures = {
        "image/png": b"\x89PNG\r\n\x1a\n",
        "image/jpeg": b"\xff\xd8\xff",
        "image/gif": b"GIF8",
    }
    signature = signatures.get(kind)
    valid = bool(content.startswith(signature)) if signature else True
    return valid, "media_signature" if signature else "nonempty", (
        "" if valid else "media signature is invalid")
