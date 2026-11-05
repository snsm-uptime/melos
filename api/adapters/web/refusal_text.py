"""A site's refusal page as plain text for the admin (spec 067 R5). Pure, stdlib only.

Drops `script`, `style`, `noscript` and `template` content, keeps the text and `mailto:` link
targets (licensing contacts), unescapes entities, collapses whitespace and cuts to 1,000
characters on a word boundary. Anything that is not HTML gives "". Also holds the body decoding
shared with the page fetcher.
"""

from __future__ import annotations

import codecs
import re
from html.parser import HTMLParser

MAX_CHARS = 1000
_HTML_TYPES = ("text/html", "application/xhtml+xml")
_HIDDEN = frozenset({"script", "style", "noscript", "template"})
_META_CHARSET = re.compile(rb"""<meta[^>]+charset\s*=\s*["']?\s*([A-Za-z0-9_\-:.]+)""", re.I)
_SPACE = re.compile(r"\s+")


def media_type(content_type: str) -> str:
    return content_type.split(";", 1)[0].strip().lower()


def _charset(content_type: str) -> str | None:
    for param in content_type.split(";")[1:]:
        name, _, value = param.partition("=")
        if name.strip().lower() == "charset" and value.strip():
            return value.strip().strip("\"'")
    return None


def decode(data: bytes, content_type: str) -> str:
    """The header charset, else a meta charset, else UTF-8, always with replacement."""
    candidates = [_charset(content_type)]
    match = _META_CHARSET.search(data[:2048])
    if match:
        candidates.append(match.group(1).decode("ascii", "ignore"))
    for name in candidates:
        if not name:
            continue
        try:
            codecs.lookup(name)
        except LookupError:
            continue
        return data.decode(name, errors="replace")
    return data.decode("utf-8", errors="replace")


class _TextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._hidden = 0
        self._mailto: list[tuple[str | None, int]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in _HIDDEN:
            self._hidden += 1
            return
        if tag == "a":
            href = dict(attrs).get("href") or ""
            target = href[7:].split("?", 1)[0].strip() if href.lower().startswith("mailto:") else ""
            self._mailto.append((target or None, len(self.parts)))
        # Block-level and line breaks separate words.
        self.parts.append(" ")

    def handle_endtag(self, tag: str) -> None:
        if tag in _HIDDEN:
            self._hidden = max(0, self._hidden - 1)
            return
        if tag == "a" and self._mailto:
            target, start = self._mailto.pop()
            if target and target not in "".join(self.parts[start:]):
                self.parts.append(f" ({target})")
        self.parts.append(" ")

    def handle_data(self, data: str) -> None:
        if not self._hidden:
            self.parts.append(data)


def refusal_text(data: bytes, content_type: str) -> str:
    if not data or media_type(content_type) not in _HTML_TYPES:
        return ""
    parser = _TextParser()
    try:
        parser.feed(decode(data, content_type))
        parser.close()
    except Exception:  # a broken page gives what was read so far
        pass
    text = _SPACE.sub(" ", "".join(parser.parts).replace("\xa0", " ")).strip()
    # "word ." from separate inline tags reads better as "word."
    text = re.sub(r" ([.,;:!?)])", r"\1", text)
    return _cut(text)


def _cut(text: str) -> str:
    if len(text) <= MAX_CHARS:
        return text
    head = text[: MAX_CHARS + 1]
    space = head.rfind(" ")
    return (head[:space] if space > 0 else text[:MAX_CHARS]).rstrip()
