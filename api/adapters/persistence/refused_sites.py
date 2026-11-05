"""RefusedSiteLog adapters (spec 067 R3, R4, R6).

`SqlRefusedSiteLog` counts one refusal per registrable domain and one HMAC fingerprint per
(domain, member), inside a SAVEPOINT so a failed write never poisons the request's session. It
stores neither the host nor the user id. `NullRefusedSiteLog` records nothing (no secret set).
"""

from __future__ import annotations

import hashlib
import hmac
from uuid import UUID

import tldextract
from sqlalchemy import text
from sqlalchemy.orm import Session

MESSAGE_MAX_CHARS = 1000
_KEY_LABEL = b"melos-refused-site-v1"

# The bundled public-suffix snapshot only: no network call, ever (R3).
_EXTRACT = tldextract.TLDExtract(suffix_list_urls=())

_UPSERT_SITE = text(
    """
    INSERT INTO refused_site
        (domain, total_refusals, distinct_members, first_seen_at, last_seen_at,
         last_status, last_message)
    VALUES (:domain, 1, 0, now(), now(), :status, :message)
    ON CONFLICT (domain) DO UPDATE SET
        total_refusals = refused_site.total_refusals + 1,
        last_seen_at = now(),
        last_status = EXCLUDED.last_status,
        last_message = EXCLUDED.last_message
    """
)
_INSERT_MEMBER = text(
    "INSERT INTO refused_site_member (domain, member_key) VALUES (:domain, :key) "
    "ON CONFLICT DO NOTHING"
)
_COUNT_MEMBER = text(
    "UPDATE refused_site SET distinct_members = distinct_members + 1 WHERE domain = :domain"
)


def derive_key(session_secret: str) -> bytes:
    """A key of its own, derived from SESSION_SECRET, which is only read (R4)."""
    return hmac.new(session_secret.encode(), _KEY_LABEL, hashlib.sha256).digest()


def registrable_domain(host: str) -> str:
    host = host.strip().rstrip(".").lower()
    parts = _EXTRACT(host)
    if parts.domain and parts.suffix:
        return f"{parts.domain}.{parts.suffix}"
    return host


def member_key(key: bytes, domain: str, user_id: UUID) -> bytes:
    return hmac.new(key, f"{domain}\n{user_id}".encode(), hashlib.sha256).digest()


class SqlRefusedSiteLog:
    def __init__(self, session: Session, *, key: bytes) -> None:
        self._session = session
        self._key = key

    def record(self, host: str, actor_user_id: UUID, status: int, message: str) -> None:
        domain = registrable_domain(host)
        with self._session.begin_nested():
            self._session.execute(
                _UPSERT_SITE,
                {"domain": domain, "status": status, "message": message[:MESSAGE_MAX_CHARS]},
            )
            fingerprint = member_key(self._key, domain, actor_user_id)
            added = self._session.execute(_INSERT_MEMBER, {"domain": domain, "key": fingerprint})
            if added.rowcount == 1:  # type: ignore[attr-defined]
                self._session.execute(_COUNT_MEMBER, {"domain": domain})


class NullRefusedSiteLog:
    def record(self, host: str, actor_user_id: UUID, status: int, message: str) -> None:
        return None
