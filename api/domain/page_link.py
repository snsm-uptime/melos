"""Link rules for link capture, and the public-address check (spec 026, research R2 and R5).

Pure: stdlib `urllib.parse` and `ipaddress` only, no I/O. The api applies these rules to the
member's link before any request, and again to every redirect target and photo address. The
ui mirrors the link rules only to enable its button (`ui/lib/capture/linkRules.ts`).
"""

from __future__ import annotations

import ipaddress
import re
from dataclasses import dataclass
from typing import Literal
from urllib.parse import urlsplit, urlunsplit

from domain.errors import DomainError

MAX_LINK_CHARS = 2048
ALLOWED_PORTS = (80, 443)
_DEFAULT_PORTS = {"http": 80, "https": 443}

LinkRefusalKind = Literal["empty", "too_long", "invalid", "credentials", "port"]

# A scheme followed by "://", as in "https://example.test".
_SCHEME_WITH_SLASHES = re.compile(r"^[A-Za-z][A-Za-z0-9+.\-]*://")
# A scheme with no slashes, as in "javascript:alert(1)"; "example.test:8080/" is a host and port.
_BARE_SCHEME = re.compile(r"^[A-Za-z][A-Za-z0-9+.\-]*:(?!\d)")
_WHITESPACE = re.compile(r"\s")


class PageLinkRefused(DomainError):
    """The link breaks a rule, so nothing is fetched. `kind` says which rule."""

    def __init__(self, kind: LinkRefusalKind) -> None:
        super().__init__(kind)
        self.kind: LinkRefusalKind = kind


@dataclass(frozen=True, slots=True)
class PageLink:
    url: str
    scheme: str
    host: str
    port: int


def normalize_link(raw: str) -> PageLink:
    """The member's link, trimmed and with `https://` added when it has no scheme."""
    text = raw.strip()
    if not text:
        raise PageLinkRefused("empty")
    if len(text) > MAX_LINK_CHARS:
        raise PageLinkRefused("too_long")
    if _WHITESPACE.search(text):
        raise PageLinkRefused("invalid")
    if not _SCHEME_WITH_SLASHES.match(text):
        if _BARE_SCHEME.match(text):
            raise PageLinkRefused("invalid")
        text = "https://" + text
    return check_link(text)


def check_link(url: str) -> PageLink:
    """Check an absolute link (also each redirect target). Raises PageLinkRefused."""
    if not url or len(url) > MAX_LINK_CHARS:
        raise PageLinkRefused("empty" if not url else "too_long")
    if _WHITESPACE.search(url) or not _SCHEME_WITH_SLASHES.match(url):
        raise PageLinkRefused("invalid")
    try:
        parts = urlsplit(url)
        explicit_port = parts.port
    except ValueError as exc:
        raise PageLinkRefused("invalid") from exc

    scheme = parts.scheme.lower()
    if scheme not in _DEFAULT_PORTS:
        raise PageLinkRefused("invalid")
    if parts.username is not None or parts.password is not None:
        raise PageLinkRefused("credentials")
    hostname = parts.hostname
    if not hostname:
        raise PageLinkRefused("invalid")
    if explicit_port is not None and explicit_port not in ALLOWED_PORTS:
        raise PageLinkRefused("port")

    host = _encode_host(hostname)
    port = explicit_port if explicit_port is not None else _DEFAULT_PORTS[scheme]
    netloc = f"[{host}]" if ":" in host else host
    if port != _DEFAULT_PORTS[scheme]:
        netloc = f"{netloc}:{port}"
    normalized = urlunsplit((scheme, netloc, parts.path or "/", parts.query, ""))
    if len(normalized) > MAX_LINK_CHARS:
        raise PageLinkRefused("too_long")
    return PageLink(url=normalized, scheme=scheme, host=host, port=port)


def _encode_host(hostname: str) -> str:
    host = hostname.lower().rstrip(".")
    if not host:
        raise PageLinkRefused("invalid")
    if ":" in host:  # IPv6 literal, already without brackets
        try:
            ipaddress.IPv6Address(host.split("%", 1)[0])
        except ValueError as exc:
            raise PageLinkRefused("invalid") from exc
        return host
    if host.isascii():
        return host
    try:
        return host.encode("idna").decode("ascii")
    except UnicodeError as exc:
        raise PageLinkRefused("invalid") from exc


def is_public_address(text: str) -> bool:
    """True only for a global unicast address, also checking any IPv4 embedded in an IPv6 one."""
    try:
        address = ipaddress.ip_address(text.strip().strip("[]").split("%", 1)[0])
    except ValueError:
        return False
    if not _is_public(address):
        return False
    if isinstance(address, ipaddress.IPv6Address):
        embedded: list[ipaddress.IPv4Address] = []
        if address.ipv4_mapped is not None:
            embedded.append(address.ipv4_mapped)
        if address.sixtofour is not None:
            embedded.append(address.sixtofour)
        if address.teredo is not None:
            embedded.extend(address.teredo)
        return all(_is_public(inner) for inner in embedded)
    return True


def _is_public(address: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    return address.is_global and not address.is_multicast
