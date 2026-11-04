"""HttpxPageFetcher with an injected resolver and httpx.MockTransport: no network (spec 026 T009).

Covers SC-003 at the adapter: blocked addresses (also when one of several is blocked), the
address pin, redirects, status, type, size and time limits, headers, and the photo rules.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Iterator
from pathlib import Path

import httpx
import pytest
from adapters.web import page_fetcher
from adapters.web.page_fetcher import MAX_BYTES, HttpxPageFetcher
from application.ports import FetchedImage, FetchedPage, PageFetchFailed

PAGES = Path(__file__).parent / "fixtures" / "pages"
PUBLIC = "93.184.216.34"
PUBLIC_6 = "2606:2800:220:1::1"
HTML = "text/html; charset=utf-8"


class FakeClock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


Handler = Callable[[httpx.Request], httpx.Response]


def _fetcher(
    handler: Handler,
    dns: dict[str, list[str]] | None = None,
    clock: FakeClock | None = None,
) -> tuple[HttpxPageFetcher, list[httpx.Request]]:
    seen: list[httpx.Request] = []
    table = {"example.test": [PUBLIC], "photos.example.test": [PUBLIC]} | (dns or {})

    def record(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return handler(request)

    def resolver(host: str) -> list[str]:
        if host not in table:
            raise OSError("no such host")
        return table[host]

    fetcher = HttpxPageFetcher(
        resolver=resolver,
        transport=httpx.MockTransport(record),
        clock=clock or FakeClock(),
    )
    return fetcher, seen


def _html(body: str = "<html><body><p>soup</p></body></html>", **headers: str) -> httpx.Response:
    return httpx.Response(200, headers={"content-type": HTML, **headers}, content=body.encode())


def test_fetches_a_public_page() -> None:
    fetcher, seen = _fetcher(lambda request: _html())

    result = fetcher.fetch_page("https://example.test/soup?x=1")

    assert result == FetchedPage(
        final_url="https://example.test/soup?x=1",
        html="<html><body><p>soup</p></body></html>",
        byte_count=37,
    )
    assert len(seen) == 1


def test_connects_to_the_checked_address_with_the_original_host() -> None:
    fetcher, seen = _fetcher(lambda request: _html())

    fetcher.fetch_page("https://example.test/soup?x=1")

    request = seen[0]
    assert request.url.host == PUBLIC
    assert request.url.path == "/soup"
    assert request.url.query == b"x=1"
    assert request.headers["host"] == "example.test"
    assert request.extensions["sni_hostname"] == "example.test"


def test_pins_an_ipv6_address() -> None:
    fetcher, seen = _fetcher(lambda request: _html(), dns={"six.example.test": [PUBLIC_6]})

    assert isinstance(fetcher.fetch_page("http://six.example.test/"), FetchedPage)
    assert seen[0].url.host == PUBLIC_6
    assert seen[0].headers["host"] == "six.example.test"


@pytest.mark.parametrize(
    "addresses",
    [
        ["127.0.0.1"],
        ["10.0.0.1"],
        ["169.254.169.254"],
        ["fd00:ec2::254"],
        ["::ffff:127.0.0.1"],
        ["100.64.0.1"],
        [PUBLIC, "192.168.1.1"],
        ["::1", PUBLIC],
        [],
    ],
)
def test_a_host_with_any_blocked_address_is_refused_without_a_request(
    addresses: list[str],
) -> None:
    fetcher, seen = _fetcher(lambda request: _html(), dns={"rebind.example.test": addresses})

    assert fetcher.fetch_page("https://rebind.example.test/") == PageFetchFailed("blocked")
    assert seen == []


@pytest.mark.parametrize(
    "url",
    ["http://127.0.0.1/", "http://[::1]/", "http://169.254.169.254/latest/meta-data/"],
)
def test_an_ip_literal_is_checked_without_dns(url: str) -> None:
    fetcher, seen = _fetcher(lambda request: _html())

    assert fetcher.fetch_page(url) == PageFetchFailed("blocked")
    assert seen == []


@pytest.mark.parametrize(
    "url", ["https://example.test:8080/", "https://user:pw@example.test/", "ftp://example.test/"]
)
def test_a_link_that_breaks_the_rules_is_refused_without_a_request(url: str) -> None:
    fetcher, seen = _fetcher(lambda request: _html())

    assert fetcher.fetch_page(url) == PageFetchFailed("blocked")
    assert seen == []


def test_unknown_host_gives_dns() -> None:
    fetcher, seen = _fetcher(lambda request: _html())

    assert fetcher.fetch_page("https://nowhere.example.test/") == PageFetchFailed("dns")
    assert seen == []


def _redirect(location: str | None, status: int = 302) -> httpx.Response:
    headers = {"location": location} if location is not None else {}
    return httpx.Response(status, headers=headers)


@pytest.mark.parametrize("status", [301, 302, 303, 307, 308])
def test_follows_a_redirect_and_returns_the_final_address(status: int) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/old":
            return _redirect("/new?y=2", status)
        return _html()

    fetcher, seen = _fetcher(handler)

    result = fetcher.fetch_page("https://example.test/old")

    assert isinstance(result, FetchedPage)
    assert result.final_url == "https://example.test/new?y=2"
    assert [request.url.path for request in seen] == ["/old", "/new"]


@pytest.mark.parametrize(
    "location",
    [
        "http://127.0.0.1/",
        "http://[::1]/admin",
        "https://example.test:8080/",
        "http://metadata.example.test/",
        "file:///etc/passwd",
    ],
)
def test_a_redirect_to_a_blocked_target_is_refused(location: str) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return _redirect(location) if request.url.path == "/" else _html()

    fetcher, seen = _fetcher(handler, dns={"metadata.example.test": ["169.254.169.254"]})

    assert fetcher.fetch_page("https://example.test/") == PageFetchFailed("blocked")
    assert len(seen) == 1


def test_three_redirects_pass_and_four_fail() -> None:
    def chain(limit: int) -> Handler:
        def handler(request: httpx.Request) -> httpx.Response:
            step = int(request.url.path.strip("/") or 0)
            return _redirect(f"/{step + 1}") if step < limit else _html()

        return handler

    three, _ = _fetcher(chain(3))
    four, seen = _fetcher(chain(4))

    assert isinstance(three.fetch_page("https://example.test/"), FetchedPage)
    assert four.fetch_page("https://example.test/") == PageFetchFailed("redirect")
    assert len(seen) == 4


def test_a_redirect_without_location_fails() -> None:
    fetcher, _ = _fetcher(lambda request: _redirect(None))

    assert fetcher.fetch_page("https://example.test/") == PageFetchFailed("redirect")


@pytest.mark.parametrize("status", [404, 403, 402, 401, 410, 429, 500, 503, 304, 100])
def test_other_status_codes_fail(status: int) -> None:
    fetcher, _ = _fetcher(lambda request: httpx.Response(status, headers={"content-type": HTML}))

    assert fetcher.fetch_page("https://example.test/") == PageFetchFailed("status")


@pytest.mark.parametrize(
    "content_type", ["application/pdf", "application/json", "image/png", "", "text/plain"]
)
def test_a_page_that_is_not_html_fails(content_type: str) -> None:
    headers = {"content-type": content_type} if content_type else {}
    fetcher, _ = _fetcher(lambda request: httpx.Response(200, headers=headers, content=b"%PDF"))

    assert fetcher.fetch_page("https://example.test/menu.pdf") == PageFetchFailed("not_html")


def test_xhtml_is_html() -> None:
    fetcher, _ = _fetcher(
        lambda request: httpx.Response(
            200, headers={"content-type": "application/xhtml+xml"}, content=b"<html/>"
        )
    )

    assert isinstance(fetcher.fetch_page("https://example.test/"), FetchedPage)


def test_a_large_content_length_fails_before_the_body() -> None:
    read: list[int] = []

    def body() -> Iterator[bytes]:
        read.append(1)
        yield b"x"

    fetcher, _ = _fetcher(
        lambda request: httpx.Response(
            200,
            headers={"content-type": HTML, "content-length": "3000000"},
            content=body(),
        )
    )

    assert fetcher.fetch_page("https://example.test/") == PageFetchFailed("too_large")
    assert read == []


def test_a_streamed_body_over_the_limit_fails() -> None:
    def body() -> Iterator[bytes]:
        for _ in range(MAX_BYTES // 65536):
            yield b"a" * 65536
        yield b"b"

    fetcher, _ = _fetcher(
        lambda request: httpx.Response(200, headers={"content-type": HTML}, content=body())
    )

    assert MAX_BYTES == 2 * 1024 * 1024
    assert fetcher.fetch_page("https://example.test/") == PageFetchFailed("too_large")


def test_a_body_exactly_at_the_limit_passes() -> None:
    fetcher, _ = _fetcher(
        lambda request: httpx.Response(
            200, headers={"content-type": HTML}, content=b"a" * MAX_BYTES
        )
    )

    result = fetcher.fetch_page("https://example.test/")

    assert isinstance(result, FetchedPage)
    assert result.byte_count == MAX_BYTES


def test_a_slow_body_fails_at_the_deadline() -> None:
    clock = FakeClock()

    def body() -> Iterator[bytes]:
        for _ in range(5):
            clock.now += 4.0
            yield b"<p>slow</p>"

    fetcher, _ = _fetcher(
        lambda request: httpx.Response(200, headers={"content-type": HTML}, content=body()),
        clock=clock,
    )

    assert fetcher.fetch_page("https://example.test/") == PageFetchFailed("timeout")


def test_a_transport_timeout_and_a_connect_error_map_to_kinds() -> None:
    def slow(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("slow", request=request)

    def refused(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused", request=request)

    def broken(request: httpx.Request) -> httpx.Response:
        raise RuntimeError("anything")

    assert _fetcher(slow)[0].fetch_page("https://example.test/") == PageFetchFailed("timeout")
    assert _fetcher(refused)[0].fetch_page("https://example.test/") == PageFetchFailed("connect")
    assert _fetcher(broken)[0].fetch_page("https://example.test/") == PageFetchFailed("connect")


def test_sends_no_personal_headers_and_a_fixed_user_agent() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/":
            return httpx.Response(302, headers={"location": "/next", "set-cookie": "sid=abc"})
        return _html()

    fetcher, seen = _fetcher(handler)

    fetcher.fetch_page("https://example.test/")
    fetcher.fetch_page("https://example.test/")

    for request in seen:
        assert "cookie" not in request.headers
        assert "authorization" not in request.headers
        assert "referer" not in request.headers
        assert request.headers["user-agent"] == "MelosRecipeImport/1.0"


def test_charset_from_the_header() -> None:
    body = "<p>Jalapeño</p>".encode("latin-1")
    fetcher, _ = _fetcher(
        lambda request: httpx.Response(
            200, headers={"content-type": "text/html; charset=ISO-8859-1"}, content=body
        )
    )

    result = fetcher.fetch_page("https://example.test/")

    assert isinstance(result, FetchedPage)
    assert result.html == "<p>Jalapeño</p>"


def test_charset_from_a_meta_tag_then_utf8_with_replacement() -> None:
    meta = '<meta charset="windows-1252"><p>Crème</p>'.encode("cp1252")
    broken = b"<p>caf\xe9</p>"
    fetcher, _ = _fetcher(
        lambda request: httpx.Response(
            200,
            headers={"content-type": "text/html"},
            content=meta if request.url.path == "/meta" else broken,
        )
    )

    with_meta = fetcher.fetch_page("https://example.test/meta")
    without = fetcher.fetch_page("https://example.test/plain")

    assert isinstance(with_meta, FetchedPage) and "Crème" in with_meta.html
    assert isinstance(without, FetchedPage) and without.html == "<p>caf�</p>"


def test_logs_the_kind_and_host_only(
    caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Alembic's fileConfig, run by the integration fixtures, disables existing loggers.
    monkeypatch.setattr(page_fetcher.logger, "disabled", False)
    fetcher, _ = _fetcher(lambda request: httpx.Response(404))

    with caplog.at_level(logging.DEBUG):
        fetcher.fetch_page("https://example.test/private/path?token=s3cret")

    text = caplog.text
    assert "status" in text and "example.test" in text
    assert "private" not in text and "s3cret" not in text and PUBLIC not in text


# --- photos ---


@pytest.mark.parametrize(
    ("name", "media_type"),
    [("photo.jpg", "image/jpeg"), ("photo.png", "image/png"), ("photo.webp", "image/webp")],
)
def test_fetch_image_by_magic_bytes(name: str, media_type: str) -> None:
    data = (PAGES / name).read_bytes()
    fetcher, seen = _fetcher(
        lambda request: httpx.Response(
            200, headers={"content-type": "application/octet-stream"}, content=data
        )
    )

    assert fetcher.fetch_image("https://photos.example.test/a") == FetchedImage(media_type, data)
    assert seen[0].headers["host"] == "photos.example.test"


def test_fetch_image_refuses_other_bytes() -> None:
    svg = b'<svg xmlns="http://www.w3.org/2000/svg"></svg>'
    other = (PAGES / "not_image.bin").read_bytes()
    fetcher, _ = _fetcher(
        lambda request: httpx.Response(
            200,
            headers={
                "content-type": "image/svg+xml" if request.url.path == "/svg" else "image/png"
            },
            content=svg if request.url.path == "/svg" else other,
        )
    )

    assert fetcher.fetch_image("https://photos.example.test/svg") is None
    assert fetcher.fetch_image("https://photos.example.test/bin") is None


def test_fetch_image_refuses_too_large_and_slow() -> None:
    clock = FakeClock()
    jpeg = (PAGES / "photo.jpg").read_bytes()

    def slow() -> Iterator[bytes]:
        yield jpeg[:10]
        clock.now += 6.0
        yield jpeg[10:]

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/big":
            return httpx.Response(200, content=jpeg[:3] + b"\0" * MAX_BYTES)
        return httpx.Response(200, content=slow())

    fetcher, _ = _fetcher(handler, clock=clock)

    assert fetcher.fetch_image("https://photos.example.test/big") is None
    assert fetcher.fetch_image("https://photos.example.test/slow") is None


def test_fetch_image_refuses_private_addresses_and_failures() -> None:
    fetcher, seen = _fetcher(
        lambda request: httpx.Response(404), dns={"inside.example.test": ["10.0.0.5"]}
    )

    assert fetcher.fetch_image("http://inside.example.test/a.jpg") is None
    assert fetcher.fetch_image("http://127.0.0.1/a.jpg") is None
    assert seen == []
    assert fetcher.fetch_image("https://photos.example.test/missing.jpg") is None
    assert fetcher.fetch_image("not a link") is None
