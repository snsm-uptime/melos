"""Stand-in PageFetcher for tests (spec 026). Never opens a socket."""

from __future__ import annotations

import threading
from dataclasses import dataclass, field

from application.ports import FetchedImage, FetchedPage, PageFetchFailed


@dataclass(slots=True)
class FakePageFetcher:
    """Answers from fixed dicts and records every call as ("page" | "image", url).

    An unknown page gives `PageFetchFailed("dns")`; an unknown image gives `None`.
    """

    pages: dict[str, FetchedPage | PageFetchFailed] = field(default_factory=dict)
    images: dict[str, FetchedImage | None] = field(default_factory=dict)
    calls: list[tuple[str, str]] = field(default_factory=list)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def fetch_page(self, url: str) -> FetchedPage | PageFetchFailed:
        with self._lock:
            self.calls.append(("page", url))
        return self.pages.get(url, PageFetchFailed("dns"))

    def fetch_image(self, url: str) -> FetchedImage | None:
        with self._lock:
            self.calls.append(("image", url))
        return self.images.get(url)
