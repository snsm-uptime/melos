"""FastAPI dependencies."""

from __future__ import annotations

import uuid
from collections.abc import Iterator

from adapters.llm.gemini_extractor import GeminiRecipeExtractor

# MVP-OUT: from adapters.llm.vocabulary import load_vocabulary, load_vocabulary_documents
from adapters.persistence.db import get_session_factory
from adapters.persistence.ingredient_catalog import SqlAlchemyIngredientCatalog
from adapters.persistence.notebooks import (
    SqlAlchemyNotebookRepository,
    SqlAlchemyTransactionCommitter,
    SqlAlchemyUserDefaultNotebook,
)
from adapters.persistence.password_hasher import Argon2PasswordHasher
from adapters.persistence.recipe_lists import SqlAlchemyRecipeListRepository
from adapters.persistence.recipes import SqlAlchemyRecipeRepository
from adapters.persistence.repositories import (
    SqlAlchemyAuthUserRepository,
    SqlAlchemyKitchenRepository,
)
from adapters.persistence.sessions import SqlAlchemySessionStore
from application.notebooks import ResolveCaptureNotebookService
from application.ports import PasswordHasher, PreferencesRepository, SessionStore
from application.rate_limit import SlidingWindowRateLimiter, resolve_trusted_client_ip
from application.recipe_capture import CaptureRecipeText
from application.recipe_extraction import RecipeExtraction
from application.recipe_lists import ListKitchenRecipesService, ListNotebookRecipesService
from application.recipe_save import SaveRecipeDraft
from application.recipe_vocabulary import vocabulary_answer
from domain.errors import AliasRequiredError
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from api.settings import (
    AuthSettings,
    load_auth_settings,
    load_gemini_settings,
    load_recipe_text_max_chars,
)


def get_db() -> Iterator[Session]:
    factory = get_session_factory()
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_password_hasher() -> PasswordHasher:
    return Argon2PasswordHasher()


def get_session_store(db: Session = Depends(get_db)) -> SessionStore:
    return SqlAlchemySessionStore(db)


def get_preferences_repository(db: Session = Depends(get_db)) -> PreferencesRepository:
    return SqlAlchemyAuthUserRepository(db)


def get_auth_settings(request: Request) -> AuthSettings:
    cached = getattr(request.app.state, "auth_settings", None)
    if cached is None:
        cached = load_auth_settings()
        request.app.state.auth_settings = cached
    return cached


def get_rate_limiter(request: Request) -> SlidingWindowRateLimiter:
    limiter = getattr(request.app.state, "rate_limiter", None)
    if limiter is None:
        limiter = SlidingWindowRateLimiter()
        request.app.state.rate_limiter = limiter
    return limiter


def resolve_request_client_ip(request: Request, settings: AuthSettings) -> str:
    """Trusted client IP for rate-limit keys (BFF header only from TRUSTED_PROXY_IPS)."""
    peer = request.client.host if request.client is not None else "unknown"
    return resolve_trusted_client_ip(
        peer_host=peer,
        header_value=request.headers.get(settings.auth_client_ip_header),
        trusted_proxies=settings.trusted_proxy_ips,
    )


def require_authenticated_user(
    request: Request,
    sessions: SessionStore = Depends(get_session_store),
    settings: AuthSettings = Depends(get_auth_settings),
) -> uuid.UUID:
    """Authentication gate for protected API routes (membership ACL lives in application/)."""
    token = request.cookies.get(settings.session_cookie_name)
    user_id = sessions.resolve_user_id(token)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated.",
        )
    return user_id


def require_user_alias(
    user_id: uuid.UUID = Depends(require_authenticated_user),
    prefs: PreferencesRepository = Depends(get_preferences_repository),
) -> uuid.UUID:
    """Kitchen surfaces need a person label; accounts without an alias are sent to setup."""
    row = prefs.get_preferences(user_id)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated.",
        )
    if not row.alias:
        raise AliasRequiredError()
    return user_id


def get_vocabulary_answer(request: Request) -> dict:
    """The lists for GET /recipe-vocabulary, built once per process (spec 016 FR-011)."""
    cached = getattr(request.app.state, "recipe_vocabulary_answer", None)
    if cached is None:
        # MVP-OUT: categories, cuisine = load_vocabulary_documents()
        cached = vocabulary_answer(max_text_chars=load_recipe_text_max_chars())
        request.app.state.recipe_vocabulary_answer = cached
    return cached


def get_recipe_extraction(request: Request) -> RecipeExtraction:
    """The S-015 use case, one per process so concurrent identical texts share a call (FR-016)."""
    cached = getattr(request.app.state, "recipe_extraction", None)
    if cached is None:
        settings = load_gemini_settings()
        # MVP-OUT: vocabulary = load_vocabulary()
        extractor = GeminiRecipeExtractor(
            api_key=settings.api_key,
            model=settings.chat_model,
            # MVP-OUT: vocabulary=vocabulary,
        )
        cached = RecipeExtraction(extractor)
        request.app.state.recipe_extraction = cached
    return cached


def get_capture_recipe_text(
    db: Session = Depends(get_db),
    extraction: RecipeExtraction = Depends(get_recipe_extraction),
) -> CaptureRecipeText:
    settings = load_gemini_settings()
    return CaptureRecipeText(
        SqlAlchemyNotebookRepository(db),
        SqlAlchemyIngredientCatalog(db),
        extraction,
        max_chars=load_recipe_text_max_chars(),
        timeout_s=settings.text_timeout_s,
    )


def get_save_recipe_draft(db: Session = Depends(get_db)) -> SaveRecipeDraft:
    notebooks = SqlAlchemyNotebookRepository(db)
    catalog = SqlAlchemyIngredientCatalog(db)
    return SaveRecipeDraft(
        notebooks,
        catalog,
        SqlAlchemyRecipeRepository(db),
        ResolveCaptureNotebookService(
            SqlAlchemyKitchenRepository(db),
            notebooks,
            SqlAlchemyUserDefaultNotebook(db),
            SqlAlchemyAuthUserRepository(db),
            catalog,
            SqlAlchemyTransactionCommitter(db),
        ),
        max_text_chars=load_recipe_text_max_chars(),
    )


def get_list_notebook_recipes(db: Session = Depends(get_db)) -> ListNotebookRecipesService:
    return ListNotebookRecipesService(
        SqlAlchemyNotebookRepository(db), SqlAlchemyRecipeListRepository(db)
    )


def get_list_kitchen_recipes(db: Session = Depends(get_db)) -> ListKitchenRecipesService:
    return ListKitchenRecipesService(
        SqlAlchemyKitchenRepository(db),
        SqlAlchemyNotebookRepository(db),
        SqlAlchemyRecipeListRepository(db),
    )
