"""Collect a page's schema.org JSON-LD blocks and its og:image tag (spec 026, research R6).

stdlib `html.parser` and `json` only. A block that fails to parse is skipped; bad HTML never
raises.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from html.parser import HTMLParser

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class PageData:
    objects: tuple[object, ...]
    og_image: str | None


class _Collector(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.blocks: list[str] = []
        self.og_image: str | None = None
        self._buffer: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {name.lower(): (value or "") for name, value in attrs}
        if tag == "script":
            media_type = values.get("type", "").split(";", 1)[0].strip().lower()
            if media_type == "application/ld+json":
                self._buffer = []
        elif tag == "meta" and self.og_image is None:
            if values.get("property", "").strip().lower() == "og:image":
                content = values.get("content", "").strip()
                if content:
                    self.og_image = content

    def handle_data(self, data: str) -> None:
        if self._buffer is not None:
            self._buffer.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "script" and self._buffer is not None:
            self.blocks.append("".join(self._buffer))
            self._buffer = None


def read_page_data(html: str) -> PageData:
    collector = _Collector()
    try:
        collector.feed(html)
        collector.close()
    except Exception:  # html.parser is lenient; this is a last guard, never raised
        logger.info("page html could not be fully parsed")
    objects: list[object] = []
    skipped = 0
    for block in collector.blocks:
        try:
            objects.append(json.loads(block))
        except (ValueError, RecursionError):
            skipped += 1
    if skipped:
        logger.info("skipped json-ld blocks: count=%d", skipped)
    return PageData(objects=tuple(objects), og_image=collector.og_image)
