"""Auth / session / SMTP settings from environment."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field

from application.rate_limit import MAX_ATTEMPTS_CAP, RateLimitPolicy, parse_trusted_proxy_ips

logger = logging.getLogger(__name__)


def _env_bool(name: str, default: bool = False) -> bool:
    raw = (os.environ.get(name) or "").strip().lower()
    if not raw:
        return default
    return raw in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    raw = (os.environ.get(name) or "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer, got {raw!r}") from exc


def _rate_limit_policy(
    max_env: str,
    window_env: str,
    *,
    max_default: int,
    window_default: int,
) -> RateLimitPolicy:
    max_attempts = _env_int(max_env, max_default)
    window_seconds = _env_int(window_env, window_default)
    if max_attempts < 1:
        raise ValueError(f"{max_env} must be >= 1, got {max_attempts}")
    if window_seconds < 1:
        raise ValueError(f"{window_env} must be >= 1, got {window_seconds}")
    if max_attempts > MAX_ATTEMPTS_CAP:
        logger.warning(
            "%s=%s exceeds cap %s; clamping",
            max_env,
            max_attempts,
            MAX_ATTEMPTS_CAP,
        )
        max_attempts = MAX_ATTEMPTS_CAP
    return RateLimitPolicy(max_attempts=max_attempts, window_seconds=window_seconds)


@dataclass(frozen=True, slots=True)
class AuthSettings:
    session_secret: str
    session_cookie_name: str
    session_cookie_secure: bool
    session_cookie_samesite: str
    email_verification_required: bool
    public_app_url: str
    rate_limit_register: RateLimitPolicy
    rate_limit_sign_in: RateLimitPolicy
    rate_limit_password_reset_request: RateLimitPolicy
    rate_limit_verify_request: RateLimitPolicy
    auth_client_ip_header: str
    trusted_proxy_ips: tuple[str, ...]


def load_auth_settings() -> AuthSettings:
    secret = (os.environ.get("SESSION_SECRET") or "").strip()
    if not secret:
        # Allow tests / health-only boot without auth routes needing secret;
        # register/sign-in routes reject empty secret as a config presence gate.
        # Opaque session tokens are NOT HMAC'd with SESSION_SECRET (Story 1.2 review:
        # secrets.token_urlsafe stored server-side; secret remains required ops config).
        secret = ""
    samesite = (os.environ.get("SESSION_COOKIE_SAMESITE") or "lax").strip().lower()
    if samesite not in {"lax", "strict", "none"}:
        samesite = "lax"
    secure = _env_bool("SESSION_COOKIE_SECURE", default=False)
    # SameSite=None requires Secure; otherwise browsers reject the cookie.
    if samesite == "none" and not secure:
        samesite = "lax"
    public_app_url = (os.environ.get("PUBLIC_APP_URL") or "http://localhost:3000").strip()
    header_raw = (os.environ.get("AUTH_CLIENT_IP_HEADER") or "X-Melos-Client-IP").strip()
    header = header_raw or "X-Melos-Client-IP"
    # Empty TRUSTED_PROXY_IPS = never honor the client-IP header (safe for direct api hits).
    # Compose pins Docker bridge + loopback only (not blanket RFC1918).
    trusted_raw = os.environ.get("TRUSTED_PROXY_IPS")
    if trusted_raw is None:
        trusted = ()
    else:
        trusted = parse_trusted_proxy_ips(trusted_raw)
    return AuthSettings(
        session_secret=secret,
        session_cookie_name=(os.environ.get("SESSION_COOKIE_NAME") or "melos_session").strip()
        or "melos_session",
        session_cookie_secure=secure,
        session_cookie_samesite=samesite,
        email_verification_required=_env_bool("EMAIL_VERIFICATION_REQUIRED", default=False),
        public_app_url=public_app_url or "http://localhost:3000",
        rate_limit_register=_rate_limit_policy(
            "AUTH_RATE_LIMIT_REGISTER_MAX",
            "AUTH_RATE_LIMIT_REGISTER_WINDOW_SECONDS",
            max_default=5,
            window_default=3600,
        ),
        rate_limit_sign_in=_rate_limit_policy(
            "AUTH_RATE_LIMIT_SIGN_IN_MAX",
            "AUTH_RATE_LIMIT_SIGN_IN_WINDOW_SECONDS",
            max_default=20,
            window_default=900,
        ),
        rate_limit_password_reset_request=_rate_limit_policy(
            "AUTH_RATE_LIMIT_PASSWORD_RESET_REQUEST_MAX",
            "AUTH_RATE_LIMIT_PASSWORD_RESET_REQUEST_WINDOW_SECONDS",
            max_default=5,
            window_default=3600,
        ),
        rate_limit_verify_request=_rate_limit_policy(
            "AUTH_RATE_LIMIT_VERIFY_REQUEST_MAX",
            "AUTH_RATE_LIMIT_VERIFY_REQUEST_WINDOW_SECONDS",
            max_default=5,
            window_default=3600,
        ),
        auth_client_ip_header=header,
        trusted_proxy_ips=trusted,
    )


@dataclass(frozen=True, slots=True)
class GeminiSettings:
    """Gemini service settings. The key is never shown in repr or logs (FR-009, FR-013)."""

    api_key: str = field(repr=False)
    chat_model: str
    text_timeout_s: float
    image_timeout_s: float


def _env_float(name: str, default: float) -> float:
    raw = (os.environ.get(name) or "").strip()
    if not raw:
        return default
    try:
        value = float(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be a number, got {raw!r}") from exc
    if value <= 0:
        raise ValueError(f"{name} must be > 0, got {value}")
    return value


def load_recipe_text_max_chars() -> int:
    """The paste limit after trimming, in characters (spec 016 FR-002)."""
    value = _env_int("RECIPE_TEXT_MAX_CHARS", 5000)
    if value <= 0:
        raise ValueError(f"RECIPE_TEXT_MAX_CHARS must be > 0, got {value}")
    return value


def load_recipe_page_batch_chars() -> int:
    """Characters of page Markdown per assistant request in link capture (spec 026 R8).

    At most the extraction limit (10,000), because each batch is one extraction call.
    """
    value = _env_int("RECIPE_PAGE_BATCH_CHARS", 10_000)
    if not 1_000 <= value <= 10_000:
        raise ValueError(f"RECIPE_PAGE_BATCH_CHARS must be 1000 to 10000, got {value}")
    return value


def load_recipe_page_max_batches() -> int:
    """Most assistant requests per link capture (spec 026 R8)."""
    value = _env_int("RECIPE_PAGE_MAX_BATCHES", 4)
    if not 1 <= value <= 8:
        raise ValueError(f"RECIPE_PAGE_MAX_BATCHES must be 1 to 8, got {value}")
    return value


def load_gemini_settings() -> GeminiSettings:
    return GeminiSettings(
        api_key=(os.environ.get("GEMINI_API_KEY") or "").strip(),
        chat_model=(os.environ.get("GEMINI_CHAT_MODEL") or "").strip(),
        text_timeout_s=_env_float("GEMINI_TEXT_TIMEOUT_S", 10.0),
        image_timeout_s=_env_float("GEMINI_IMAGE_TIMEOUT_S", 30.0),
    )


EMBED_TEXT_STRATEGIES = ("toon", "plain")


@dataclass(frozen=True, slots=True)
class EmbeddingSettings:
    """Embeddings, the worker and search (spec 019). The key is never shown in repr or logs."""

    api_key: str = field(repr=False)
    model: str
    dimension: int
    text_timeout_s: float
    strategy: str
    worker_enabled: bool
    worker_poll_s: float
    batch_size: int
    retry_first_wait_s: float
    retry_growth: float
    retry_cap_s: float
    min_closeness: float
    record_retention_days: int

    @property
    def configured(self) -> bool:
        return bool(self.api_key) and bool(self.model)


def _env_number(name: str, default: float) -> float:
    """A float with no sign rule; the caller checks the range."""
    raw = (os.environ.get(name) or "").strip()
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be a number, got {raw!r}") from exc


def _env_positive_int(name: str, default: int) -> int:
    value = _env_int(name, default)
    if value < 1:
        raise ValueError(f"{name} must be >= 1, got {value}")
    return value


def load_embedding_settings() -> EmbeddingSettings:
    strategy = (os.environ.get("EMBED_TEXT_STRATEGY") or "toon").strip().lower() or "toon"
    if strategy not in EMBED_TEXT_STRATEGIES:
        raise ValueError(
            f"EMBED_TEXT_STRATEGY must be one of {EMBED_TEXT_STRATEGIES}, got {strategy!r}"
        )
    first = _env_float("EMBED_RETRY_FIRST_WAIT_S", 60.0)
    growth = _env_float("EMBED_RETRY_GROWTH", 1.5)
    if growth <= 1:
        raise ValueError(f"EMBED_RETRY_GROWTH must be > 1, got {growth}")
    cap = _env_float("EMBED_RETRY_CAP_S", 7200.0)
    if cap < first:
        raise ValueError(f"EMBED_RETRY_CAP_S must be >= EMBED_RETRY_FIRST_WAIT_S, got {cap}")
    closeness = _env_number("SEARCH_MIN_CLOSENESS", 0.65)
    if not -1 <= closeness <= 1:
        raise ValueError(f"SEARCH_MIN_CLOSENESS must be between -1 and 1, got {closeness}")
    return EmbeddingSettings(
        api_key=(os.environ.get("GEMINI_API_KEY") or "").strip(),
        model=(os.environ.get("GEMINI_EMBED_MODEL") or "gemini-embedding-001").strip(),
        dimension=_env_positive_int("GEMINI_EMBED_DIM", 768),
        text_timeout_s=_env_float("GEMINI_TEXT_TIMEOUT_S", 10.0),
        strategy=strategy,
        worker_enabled=_env_bool("EMBEDDING_WORKER_ENABLED", default=True),
        worker_poll_s=_env_float("EMBED_WORKER_POLL_S", 5.0),
        batch_size=_env_positive_int("EMBED_BATCH_SIZE", 1),
        retry_first_wait_s=first,
        retry_growth=growth,
        retry_cap_s=cap,
        min_closeness=closeness,
        record_retention_days=_env_positive_int("SEARCH_RECORD_RETENTION_DAYS", 180),
    )
