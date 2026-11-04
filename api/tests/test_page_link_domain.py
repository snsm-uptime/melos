"""Link rules and the public-address check for link capture (spec 026 T005, research R2 and R5)."""

from __future__ import annotations

import pytest
from domain.page_link import (
    MAX_LINK_CHARS,
    PageLinkRefused,
    check_link,
    is_public_address,
    normalize_link,
)


def _refusal(raw: str) -> str:
    with pytest.raises(PageLinkRefused) as caught:
        normalize_link(raw)
    return caught.value.kind


def test_adds_https_when_the_link_has_no_scheme() -> None:
    link = normalize_link("example.test/soup")

    assert link.url == "https://example.test/soup"
    assert (link.scheme, link.host, link.port) == ("https", "example.test", 443)


def test_trims_and_lower_cases_scheme_and_host_but_not_the_path() -> None:
    link = normalize_link("  HTTP://Example.TEST/Recipes/Soup?Id=4  ")

    assert link.url == "http://example.test/Recipes/Soup?Id=4"
    assert link.port == 80


def test_adds_a_slash_for_an_empty_path_and_drops_the_fragment() -> None:
    assert normalize_link("https://example.test").url == "https://example.test/"
    assert normalize_link("https://example.test/a#step-2").url == "https://example.test/a"


def test_idna_encodes_the_host() -> None:
    link = normalize_link("cocina.ñandú.test/tortilla")

    assert link.host == "cocina.xn--and-6ma2c.test"
    assert link.host.isascii()
    assert link.url == "https://cocina.xn--and-6ma2c.test/tortilla"


@pytest.mark.parametrize("raw", ["", "   ", "\n\t"])
def test_refuses_empty(raw: str) -> None:
    assert _refusal(raw) == "empty"


def test_refuses_whitespace_inside() -> None:
    assert _refusal("https://example.test/lentil soup") == "invalid"


def test_refuses_over_the_limit() -> None:
    raw = "https://example.test/" + "a" * MAX_LINK_CHARS

    assert MAX_LINK_CHARS == 2048
    assert _refusal(raw) == "too_long"


def test_accepts_exactly_the_limit() -> None:
    raw = "https://example.test/" + "a" * (MAX_LINK_CHARS - len("https://example.test/"))

    assert len(normalize_link(raw).url) == MAX_LINK_CHARS


@pytest.mark.parametrize(
    "raw",
    [
        "ftp://example.test/soup.txt",
        "file:///etc/passwd",
        "javascript:alert(1)",
        "mailto:cook@example.test",
        "data:text/html,hello",
        "https://",
        "https:///soup",
    ],
)
def test_refuses_other_schemes_and_links_without_a_host(raw: str) -> None:
    assert _refusal(raw) == "invalid"


@pytest.mark.parametrize("raw", ["https://user:pw@example.test/", "https://user@example.test/"])
def test_refuses_credentials(raw: str) -> None:
    assert _refusal(raw) == "credentials"


@pytest.mark.parametrize(
    "raw", ["https://example.test:8080/", "http://example.test:8443/", "example.test:22/"]
)
def test_refuses_other_ports(raw: str) -> None:
    assert _refusal(raw) == "port"


@pytest.mark.parametrize("raw", ["http://example.test:80/", "https://example.test:443/"])
def test_accepts_ports_80_and_443(raw: str) -> None:
    assert normalize_link(raw).url.startswith(raw.split(":")[0] + "://example.test")


def test_keeps_an_ip_literal_host_for_the_address_check() -> None:
    assert normalize_link("http://127.0.0.1/").host == "127.0.0.1"
    assert normalize_link("http://[::1]/").host == "::1"
    assert normalize_link("http://[::1]/").url == "http://[::1]/"


def test_check_link_never_adds_a_scheme() -> None:
    with pytest.raises(PageLinkRefused) as caught:
        check_link("example.test/soup")
    assert caught.value.kind == "invalid"

    assert check_link("https://example.test/soup").url == "https://example.test/soup"


@pytest.mark.parametrize(
    "address",
    [
        "127.0.0.1",
        "10.0.0.1",
        "172.16.0.1",
        "192.168.1.1",
        "169.254.169.254",
        "100.64.0.1",
        "0.0.0.0",
        "224.0.0.1",
        "255.255.255.255",
        "::1",
        "::",
        "fe80::1",
        "fe80::1%eth0",
        "fd00:ec2::254",
        "ff02::1",
        "::ffff:127.0.0.1",
        "::ffff:10.0.0.1",
        "2002:7f00:0001::1",
        "2002:0a00:0001::1",
        "not an address",
        "",
    ],
)
def test_blocked_addresses(address: str) -> None:
    assert is_public_address(address) is False


@pytest.mark.parametrize("address", ["93.184.216.34", "2606:2800:220:1::1", "8.8.8.8"])
def test_public_addresses(address: str) -> None:
    assert is_public_address(address) is True
