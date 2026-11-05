"""SSRF-safe PageFetcher on httpx (spec 026, research R1 to R4 and R12).

For the first request and every redirect: the link rules (`domain.page_link.check_link`), DNS in
a worker thread bounded by the remaining time, every resolved address public
(`domain.page_link.is_public_address`), then the connection goes to the checked address itself,
with the original name in the `Host` header and in TLS (`sni_hostname`), so no second lookup
can swap the address. Redirects are followed by hand, at most 3. Never raises: every problem is
a `PageFetchFailed` (page) or `None` (photo). Logs carry the kind and host only.
"""

from __future__ import annotations

import ipaddress
import logging
import socket
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeout
from dataclasses import dataclass
from urllib.parse import urljoin, urlsplit, urlunsplit

import httpx
from application.ports import (
    FetchedImage,
    FetchedPage,
    ImageMediaType,
    PageFetchFailed,
    PageFetchFailureKind,
)
from domain.page_link import PageLink, PageLinkRefused, check_link, is_public_address

from adapters.web.refusal_text import decode as _decode
from adapters.web.refusal_text import media_type as _media_type
from adapters.web.refusal_text import refusal_text

logger = logging.getLogger(__name__)
# httpx logs every request line at INFO, and httpcore every connection at DEBUG, with the full
# path, query and pinned address. Those must not reach the logs (R12), so both stay at WARNING.
for _noisy in ("httpx", "httpcore"):
    logging.getLogger(_noisy).setLevel(logging.WARNING)

PAGE_TIMEOUT_S = 10.0
IMAGE_TIMEOUT_S = 5.0
MAX_BYTES = 2 * 1024 * 1024
MAX_REDIRECTS = 3
USER_AGENT = "MelosRecipeImport/1.0"
_PAGE_ACCEPT = "text/html,application/xhtml+xml"
_IMAGE_ACCEPT = "image/jpeg,image/png,image/webp"
_HTML_TYPES = ("text/html", "application/xhtml+xml")
_REDIRECTS = frozenset({301, 302, 303, 307, 308})
# The site itself denies access (spec 067 R1); its page is read only this far, for the admin.
_REFUSALS = frozenset({401, 402, 403, 451})
REFUSAL_MAX_BYTES = 64 * 1024

Resolver = Callable[[str], list[str]]
Clock = Callable[[], float]


class _Failed(Exception):
    def __init__(
        self, kind: PageFetchFailureKind, *, status: int | None = None, message: str = ""
    ) -> None:
        super().__init__(kind)
        self.kind: PageFetchFailureKind = kind
        self.status = status
        self.message = message


def resolve_host(host: str) -> list[str]:
    """Every address the system resolver gives for the host (TCP only)."""
    infos = socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)
    return list(dict.fromkeys(str(info[4][0]) for info in infos))


@dataclass(frozen=True, slots=True)
class _Body:
    final_url: str
    content_type: str
    data: bytes


class HttpxPageFetcher:
    def __init__(
        self,
        resolver: Resolver = resolve_host,
        transport: httpx.BaseTransport | None = None,
        clock: Clock = time.monotonic,
    ) -> None:
        self._resolver = resolver
        self._clock = clock
        self._client = httpx.Client(
            transport=transport,
            follow_redirects=False,
            trust_env=False,
        )
        # DNS has no timeout of its own: run it in a thread and stop waiting at the deadline.
        self._dns = ThreadPoolExecutor(max_workers=4, thread_name_prefix="page-dns")

    def fetch_page(self, url: str) -> FetchedPage | PageFetchFailed:
        host = _host_for_log(url)
        try:
            body = self._get(url, PAGE_TIMEOUT_S, _PAGE_ACCEPT, html_only=True)
        except _Failed as failed:
            if failed.kind == "refused":
                # The site's text and the path never reach the logs (spec 026 R12).
                logger.info(
                    "page fetch failed: kind=refused status=%d host=%s", failed.status or 0, host
                )
                return PageFetchFailed("refused", status=failed.status, message=failed.message)
            logger.info("page fetch failed: kind=%s host=%s", failed.kind, host)
            return PageFetchFailed(failed.kind)
        html = _decode(body.data, body.content_type)
        logger.info("page fetched: host=%s bytes=%d", _host_for_log(body.final_url), len(body.data))
        return FetchedPage(final_url=body.final_url, html=html, byte_count=len(body.data))

    def fetch_image(self, url: str) -> FetchedImage | None:
        host = _host_for_log(url)
        try:
            body = self._get(url, IMAGE_TIMEOUT_S, _IMAGE_ACCEPT, html_only=False)
        except _Failed as failed:
            logger.info("photo fetch failed: kind=%s host=%s", failed.kind, host)
            return None
        media_type = _image_type(body.data)
        if media_type is None:
            logger.info("photo fetch failed: kind=not_image host=%s", host)
            return None
        return FetchedImage(media_type=media_type, data=body.data)

    # --- one fetch, redirects included ---

    def _get(self, url: str, budget_s: float, accept: str, *, html_only: bool) -> _Body:
        deadline = self._clock() + budget_s
        current = self._check(url)
        redirects = 0
        while True:
            address = self._resolve(current, deadline)
            request = self._request(current, address, accept, deadline)
            try:
                response = self._client.send(request, stream=True)
            except httpx.TimeoutException as exc:
                raise _Failed("timeout") from exc
            except Exception as exc:  # any transport problem, never raised to the caller
                raise _Failed("connect") from exc
            try:
                self._client.cookies.clear()
                if response.status_code in _REDIRECTS:
                    location = response.headers.get("location")
                    redirects += 1
                    if not location or redirects > MAX_REDIRECTS:
                        raise _Failed("redirect")
                    current = self._check(urljoin(current.url, location.strip()))
                    continue
                if response.status_code in _REFUSALS:
                    content_type = response.headers.get("content-type", "")
                    raise _Failed(
                        "refused",
                        status=response.status_code,
                        message=refusal_text(self._read_refusal(response, deadline), content_type),
                    )
                if not 200 <= response.status_code < 300:
                    raise _Failed("status")
                content_type = response.headers.get("content-type", "")
                if html_only and _media_type(content_type) not in _HTML_TYPES:
                    raise _Failed("not_html")
                data = self._read(response, deadline)
                return _Body(final_url=current.url, content_type=content_type, data=data)
            finally:
                response.close()

    def _check(self, url: str) -> PageLink:
        try:
            return check_link(url)
        except PageLinkRefused as exc:
            raise _Failed("blocked") from exc

    def _resolve(self, link: PageLink, deadline: float) -> str:
        if is_public_address(link.host):
            return link.host
        if _is_ip_literal(link.host):
            raise _Failed("blocked")
        remaining = deadline - self._clock()
        if remaining <= 0:
            raise _Failed("timeout")
        future = self._dns.submit(self._resolver, link.host)
        try:
            addresses = future.result(timeout=remaining)
        except FutureTimeout as exc:
            raise _Failed("timeout") from exc
        except Exception as exc:
            raise _Failed("dns") from exc
        if not addresses or not all(is_public_address(address) for address in addresses):
            raise _Failed("blocked")
        return addresses[0]

    def _request(self, link: PageLink, address: str, accept: str, deadline: float) -> httpx.Request:
        remaining = deadline - self._clock()
        if remaining <= 0:
            raise _Failed("timeout")
        parts = urlsplit(link.url)
        netloc = f"[{address}]" if ":" in address else address
        default_port = 443 if link.scheme == "https" else 80
        if link.port != default_port:
            netloc = f"{netloc}:{link.port}"
        pinned = urlunsplit((link.scheme, netloc, parts.path or "/", parts.query, ""))
        host_header = f"[{link.host}]" if ":" in link.host else link.host
        if link.port != default_port:
            host_header = f"{host_header}:{link.port}"
        # Built directly, not through client.build_request, so no cookie is ever attached.
        return httpx.Request(
            "GET",
            pinned,
            headers={
                "Host": host_header,
                "User-Agent": USER_AGENT,
                "Accept": accept,
            },
            extensions={
                "sni_hostname": link.host,
                "timeout": httpx.Timeout(remaining).as_dict(),
            },
        )

    def _read(self, response: httpx.Response, deadline: float) -> bytes:
        declared = response.headers.get("content-length")
        if declared is not None:
            try:
                if int(declared) > MAX_BYTES:
                    raise _Failed("too_large")
            except ValueError:
                pass
        chunks: list[bytes] = []
        total = 0
        try:
            # Decoded bytes, so a compressed body is capped at its real size.
            for chunk in response.iter_bytes():
                total += len(chunk)
                if total > MAX_BYTES:
                    raise _Failed("too_large")
                if self._clock() > deadline:
                    raise _Failed("timeout")
                chunks.append(chunk)
        except httpx.TimeoutException as exc:
            raise _Failed("timeout") from exc
        except httpx.HTTPError as exc:
            raise _Failed("connect") from exc
        return b"".join(chunks)

    def _read_refusal(self, response: httpx.Response, deadline: float) -> bytes:
        """At most REFUSAL_MAX_BYTES within the same deadline; any problem gives b""."""
        chunks: list[bytes] = []
        total = 0
        try:
            for chunk in response.iter_bytes():
                if self._clock() > deadline:
                    return b""
                chunks.append(chunk)
                total += len(chunk)
                if total >= REFUSAL_MAX_BYTES:
                    break
        except Exception:
            return b""
        return b"".join(chunks)[:REFUSAL_MAX_BYTES]


def _is_ip_literal(host: str) -> bool:
    try:
        ipaddress.ip_address(host.split("%", 1)[0])
    except ValueError:
        return False
    return True


def _image_type(data: bytes) -> ImageMediaType | None:
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return None


def _host_for_log(url: str) -> str:
    """The host only: a path or query can carry personal tokens (R12)."""
    try:
        return urlsplit(url).hostname or "-"
    except ValueError:
        return "-"
