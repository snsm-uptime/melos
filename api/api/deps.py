"""FastAPI dependencies."""

from __future__ import annotations

import uuid
from collections.abc import Iterator

from adapters.image.calibration import load_calibration_table
from adapters.image.pipeline import PillowPicturePipeline
from adapters.language.lingua_detector import LinguaLanguageDetector
from adapters.llm.gemini_embedder import GeminiEmbedder
from adapters.llm.gemini_extractor import GeminiRecipeExtractor
from adapters.llm.gemini_pair_suggester import GeminiPairSuggester
from adapters.persistence.admin import SqlAlchemyAdminReports
from adapters.persistence.cart_activity import SqlAlchemyCartActivityLog
from adapters.persistence.carts import (
    SqlAlchemyCartRepository,
    SqlAlchemyIngredientLineReader,
    SqlAlchemyListNameSource,
)
from adapters.persistence.co_members import SqlAlchemyCoMemberDirectory

# MVP-OUT: from adapters.llm.vocabulary import load_vocabulary, load_vocabulary_documents
from adapters.persistence.db import get_session_factory
from adapters.persistence.edit_locks import SqlAlchemyEditLockRepository, resolve_session_ref
from adapters.persistence.embeddings import SqlAlchemyEmbeddingJobs, SqlAlchemyRecipeEmbeddings
from adapters.persistence.ingredient_catalog import SqlAlchemyIngredientCatalog
from adapters.persistence.notebooks import (
    SqlAlchemyNotebookRepository,
    SqlAlchemyTransactionCommitter,
    SqlAlchemyUserDefaultNotebook,
)
from adapters.persistence.password_hasher import Argon2PasswordHasher
from adapters.persistence.places import SqlAlchemyPlaceRepository
from adapters.persistence.recipe_lists import SqlAlchemyRecipeListRepository
from adapters.persistence.recipes import SqlAlchemyRecipeRepository
from adapters.persistence.refused_sites import (
    NullRefusedSiteLog,
    SqlRefusedSiteLog,
    derive_key,
)
from adapters.persistence.repositories import (
    SqlAlchemyAuthUserRepository,
    SqlAlchemyKitchenRepository,
)
from adapters.persistence.search_records import SqlAlchemySearchRecords
from adapters.persistence.sessions import SqlAlchemySessionStore
from adapters.persistence.shopping_lists import SqlAlchemyShoppingListRepository
from adapters.persistence.units import SqlAlchemyUnitRepository
from adapters.web.page_fetcher import HttpxPageFetcher
from adapters.web.page_reader import TrafilaturaPageReader
from application.admin import AdminDashboard
from application.carts import (
    AddToDraftService,
    DiscardCartService,
    GetCartService,
    RemoveFromDraftService,
    ReplaceDraftService,
    SaveCartService,
    StartCartEditService,
)
from application.catalog_manage import (
    DeleteNameService,
    DismissPairService,
    GetCatalogService,
    MergePreviewService,
    MergeService,
    RenameService,
    SplitService,
    SuggestPairsService,
)
from application.notebooks import ResolveCaptureNotebookService
from application.ports import (
    Embedder,
    IngredientPairSuggester,
    PageFetcher,
    PageReader,
    PasswordHasher,
    PicturePipeline,
    PreferencesRepository,
    RefusedSiteLog,
    SessionRef,
    SessionStore,
    UnitRepository,
)
from application.rate_limit import SlidingWindowRateLimiter, resolve_trusted_client_ip
from application.recipe_capture import CaptureRecipeText
from application.recipe_capture_picture import CapturePictureRecipe
from application.recipe_capture_url import CaptureRecipeUrl
from application.recipe_extraction import RecipeExtraction
from application.recipe_lists import ListKitchenRecipesService, ListNotebookRecipesService
from application.recipe_locks import AcquireRecipeLockService, ReleaseRecipeLockService
from application.recipe_manage import (
    DeleteRecipeService,
    GetRecipeService,
    MatchRecipeNamesService,
    SetRecipeLanguageService,
    UpdateRecipeService,
)
from application.recipe_save import SaveRecipeDraft
from application.recipe_search import MarkSearchResultUsed, SearchRecipesService
from application.recipe_share import ListShareCandidatesService, ShareRecipeService
from application.recipe_vocabulary import vocabulary_answer
from application.shopping_list import (
    ActiveListSync,
    AddShoppingItemService,
    ClosedShoppingListsService,
    CloseShoppingListService,
    GetShoppingListService,
    RemoveShoppingItemService,
    SetItemBoughtService,
)
from domain.errors import AliasRequiredError
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from api.settings import (
    AuthSettings,
    load_auth_settings,
    load_embedding_settings,
    load_gemini_settings,
    load_recipe_page_batch_chars,
    load_recipe_page_max_batches,
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


def require_session_ref(
    request: Request,
    db: Session = Depends(get_db),
    settings: AuthSettings = Depends(get_auth_settings),
    user_id: uuid.UUID = Depends(require_user_alias),
) -> SessionRef:
    """The caller and their session, for edit locks (spec 022 research R3)."""
    ref = resolve_session_ref(db, request.cookies.get(settings.session_cookie_name))
    if ref is None or ref.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated.",
        )
    return ref


def get_unit_repository(db: Session = Depends(get_db)) -> UnitRepository:
    return SqlAlchemyUnitRepository(db)


def get_admin_dashboard(db: Session = Depends(get_db)) -> AdminDashboard:
    return AdminDashboard(SqlAlchemyAdminReports(db))


def optional_user_id(
    request: Request,
    sessions: SessionStore = Depends(get_session_store),
    settings: AuthSettings = Depends(get_auth_settings),
) -> uuid.UUID | None:
    """The caller, or None: a dashboard route must not answer 401 (spec 055 R16)."""
    return sessions.resolve_user_id(request.cookies.get(settings.session_cookie_name))


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
        # The draft's language comes from the text, offline (spec 043 FR-005a).
        cached = RecipeExtraction(extractor, LinguaLanguageDetector())
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
        units=SqlAlchemyUnitRepository(db),
        max_chars=load_recipe_text_max_chars(),
        timeout_s=settings.text_timeout_s,
    )


def get_page_fetcher(request: Request) -> PageFetcher:
    """One SSRF-safe fetcher per process (spec 026)."""
    cached = getattr(request.app.state, "page_fetcher", None)
    if cached is None:
        cached = HttpxPageFetcher()
        request.app.state.page_fetcher = cached
    return cached


def get_page_reader(request: Request) -> PageReader:
    cached = getattr(request.app.state, "page_reader", None)
    if cached is None:
        cached = TrafilaturaPageReader()
        request.app.state.page_reader = cached
    return cached


def get_capture_recipe_url(
    request: Request,
    db: Session = Depends(get_db),
    extraction: RecipeExtraction = Depends(get_recipe_extraction),
    fetcher: PageFetcher = Depends(get_page_fetcher),
    reader: PageReader = Depends(get_page_reader),
) -> CaptureRecipeUrl:
    """Link capture shares the per-process extraction use case with text capture."""
    return CaptureRecipeUrl(
        SqlAlchemyNotebookRepository(db),
        SqlAlchemyIngredientCatalog(db),
        extraction,
        fetcher,
        reader,
        units=SqlAlchemyUnitRepository(db),
        timeout_s=load_gemini_settings().text_timeout_s,
        batch_chars=load_recipe_page_batch_chars(),
        max_batches=load_recipe_page_max_batches(),
        refused_sites=_refused_site_log(request, db),
    )


def get_picture_pipeline() -> PicturePipeline:
    """Stateless, so one per request is fine (spec 041). Pillow and pillow-heif load here."""
    return PillowPicturePipeline()


def get_capture_recipe_picture(
    db: Session = Depends(get_db),
    extraction: RecipeExtraction = Depends(get_recipe_extraction),
    pipeline: PicturePipeline = Depends(get_picture_pipeline),
) -> CapturePictureRecipe:
    """Picture capture shares the per-process extraction use case (spec 041)."""
    return CapturePictureRecipe(
        SqlAlchemyNotebookRepository(db),
        SqlAlchemyIngredientCatalog(db),
        extraction,
        pipeline,
        units=SqlAlchemyUnitRepository(db),
        timeout_s=load_gemini_settings().image_timeout_s,
        table=load_calibration_table(),
    )


def _refused_site_log(request: Request, db: Session) -> RefusedSiteLog:
    """Spec 067: without SESSION_SECRET (test boot) nothing is recorded."""
    secret = get_auth_settings(request).session_secret
    if not secret:
        return NullRefusedSiteLog()
    return SqlRefusedSiteLog(db, key=derive_key(secret))


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
        units=SqlAlchemyUnitRepository(db),
        max_text_chars=load_recipe_text_max_chars(),
        embedding_jobs=SqlAlchemyEmbeddingJobs(db),
    )


def get_get_recipe(db: Session = Depends(get_db)) -> GetRecipeService:
    return GetRecipeService(
        SqlAlchemyRecipeRepository(db),
        SqlAlchemyNotebookRepository(db),
        SqlAlchemyEditLockRepository(db),
        SqlAlchemyCartRepository(db),
        catalog=SqlAlchemyIngredientCatalog(db),
    )


def get_set_recipe_language(db: Session = Depends(get_db)) -> SetRecipeLanguageService:
    return SetRecipeLanguageService(
        SqlAlchemyRecipeRepository(db),
        SqlAlchemyNotebookRepository(db),
        SqlAlchemyIngredientCatalog(db),
        SqlAlchemyEditLockRepository(db),
    )


def get_list_share_candidates(db: Session = Depends(get_db)) -> ListShareCandidatesService:
    return ListShareCandidatesService(SqlAlchemyCoMemberDirectory(db))


def get_share_recipe(db: Session = Depends(get_db)) -> ShareRecipeService:
    return ShareRecipeService(
        SqlAlchemyRecipeRepository(db),
        SqlAlchemyNotebookRepository(db),
        SqlAlchemyIngredientCatalog(db),
        SqlAlchemyAuthUserRepository(db),
        SqlAlchemyCoMemberDirectory(db),
        SqlAlchemyUserDefaultNotebook(db),
        embedding_jobs=SqlAlchemyEmbeddingJobs(db),
    )


def get_match_recipe_names(db: Session = Depends(get_db)) -> MatchRecipeNamesService:
    return MatchRecipeNamesService(
        SqlAlchemyRecipeRepository(db),
        SqlAlchemyNotebookRepository(db),
        SqlAlchemyIngredientCatalog(db),
    )


def get_update_recipe(db: Session = Depends(get_db)) -> UpdateRecipeService:
    return UpdateRecipeService(
        SqlAlchemyRecipeRepository(db),
        SqlAlchemyNotebookRepository(db),
        SqlAlchemyIngredientCatalog(db),
        SqlAlchemyEditLockRepository(db),
        units=SqlAlchemyUnitRepository(db),
        embedding_jobs=SqlAlchemyEmbeddingJobs(db),
    )


def get_delete_recipe(db: Session = Depends(get_db)) -> DeleteRecipeService:
    return DeleteRecipeService(
        SqlAlchemyRecipeRepository(db),
        SqlAlchemyNotebookRepository(db),
        SqlAlchemyEditLockRepository(db),
    )


def get_acquire_recipe_lock(db: Session = Depends(get_db)) -> AcquireRecipeLockService:
    return AcquireRecipeLockService(
        SqlAlchemyRecipeRepository(db),
        SqlAlchemyNotebookRepository(db),
        SqlAlchemyEditLockRepository(db),
    )


def get_release_recipe_lock(db: Session = Depends(get_db)) -> ReleaseRecipeLockService:
    return ReleaseRecipeLockService(SqlAlchemyEditLockRepository(db))


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


def _cart(cls, db: Session):  # noqa: ANN001, ANN202
    return cls(
        SqlAlchemyKitchenRepository(db),
        SqlAlchemyCartRepository(db),
        SqlAlchemyEditLockRepository(db),
    )


def get_get_cart(db: Session = Depends(get_db)) -> GetCartService:
    return _cart(GetCartService, db)


def get_start_cart_edit(db: Session = Depends(get_db)) -> StartCartEditService:
    return _cart(StartCartEditService, db)


def get_add_to_draft(db: Session = Depends(get_db)) -> AddToDraftService:
    return _cart(AddToDraftService, db)


def get_remove_from_draft(db: Session = Depends(get_db)) -> RemoveFromDraftService:
    return _cart(RemoveFromDraftService, db)


def get_replace_draft(db: Session = Depends(get_db)) -> ReplaceDraftService:
    return _cart(ReplaceDraftService, db)


def _shopping_list_sync(db: Session) -> ActiveListSync:
    return ActiveListSync(
        SqlAlchemyCartRepository(db),
        SqlAlchemyIngredientLineReader(db),
        SqlAlchemyShoppingListRepository(db),
        names=SqlAlchemyListNameSource(db),
    )


def get_save_cart(db: Session = Depends(get_db)) -> SaveCartService:
    return SaveCartService(
        SqlAlchemyKitchenRepository(db),
        SqlAlchemyCartRepository(db),
        SqlAlchemyEditLockRepository(db),
        _shopping_list_sync(db),
        activity=SqlAlchemyCartActivityLog(db),
    )


def get_discard_cart(db: Session = Depends(get_db)) -> DiscardCartService:
    return _cart(DiscardCartService, db)


def get_get_shopping_list(db: Session = Depends(get_db)) -> GetShoppingListService:
    return GetShoppingListService(
        SqlAlchemyKitchenRepository(db),
        SqlAlchemyCartRepository(db),
        SqlAlchemyEditLockRepository(db),
        SqlAlchemyIngredientLineReader(db),
        SqlAlchemyShoppingListRepository(db),
        SqlAlchemyPlaceRepository(db),
        names=SqlAlchemyListNameSource(db),
        prefs=SqlAlchemyAuthUserRepository(db),
    )


def _list_change(cls, db: Session):  # noqa: ANN001, ANN202
    return cls(
        SqlAlchemyKitchenRepository(db),
        SqlAlchemyCartRepository(db),
        SqlAlchemyShoppingListRepository(db),
        _shopping_list_sync(db),
        SqlAlchemyPlaceRepository(db),
    )


def get_add_shopping_item(db: Session = Depends(get_db)) -> AddShoppingItemService:
    return _list_change(AddShoppingItemService, db)


def get_remove_shopping_item(db: Session = Depends(get_db)) -> RemoveShoppingItemService:
    return _list_change(RemoveShoppingItemService, db)


def get_set_item_bought(db: Session = Depends(get_db)) -> SetItemBoughtService:
    return _list_change(SetItemBoughtService, db)


def get_close_shopping_list(db: Session = Depends(get_db)) -> CloseShoppingListService:
    return CloseShoppingListService(
        SqlAlchemyKitchenRepository(db),
        SqlAlchemyCartRepository(db),
        SqlAlchemyShoppingListRepository(db),
        _shopping_list_sync(db),
        activity=SqlAlchemyCartActivityLog(db),
        places=SqlAlchemyPlaceRepository(db),
        prefs=SqlAlchemyAuthUserRepository(db),
    )


def get_closed_shopping_lists(db: Session = Depends(get_db)) -> ClosedShoppingListsService:
    return ClosedShoppingListsService(
        SqlAlchemyKitchenRepository(db),
        SqlAlchemyCartRepository(db),
        SqlAlchemyShoppingListRepository(db),
        SqlAlchemyPlaceRepository(db),
        prefs=SqlAlchemyAuthUserRepository(db),
    )


def get_embedder(request: Request) -> Embedder:
    """One embedder per process, shared with the worker thread (spec 019)."""
    cached = getattr(request.app.state, "embedder", None)
    if cached is None:
        settings = load_embedding_settings()
        cached = GeminiEmbedder(
            api_key=settings.api_key, model=settings.model, dimension=settings.dimension
        )
        request.app.state.embedder = cached
    return cached


def get_search_recipes(
    db: Session = Depends(get_db),
    embedder: Embedder = Depends(get_embedder),
) -> SearchRecipesService:
    """For S-030, S-044 and S-032; this story adds no route (contracts/search-service.md)."""
    settings = load_embedding_settings()
    return SearchRecipesService(
        SqlAlchemyKitchenRepository(db),
        SqlAlchemyNotebookRepository(db),
        SqlAlchemyRecipeEmbeddings(db),
        embedder,
        SqlAlchemySearchRecords(db),
        strategy=settings.strategy,
        min_closeness=settings.min_closeness,
        timeout_s=settings.text_timeout_s,
    )


def get_mark_search_result_used(db: Session = Depends(get_db)) -> MarkSearchResultUsed:
    return MarkSearchResultUsed(SqlAlchemySearchRecords(db))


# --- catalog management (spec 043) ------------------------------------------------------------


def get_get_catalog(db: Session = Depends(get_db)) -> GetCatalogService:
    return GetCatalogService(SqlAlchemyNotebookRepository(db), SqlAlchemyIngredientCatalog(db))


def get_catalog_merge_preview(db: Session = Depends(get_db)) -> MergePreviewService:
    return MergePreviewService(SqlAlchemyNotebookRepository(db), SqlAlchemyIngredientCatalog(db))


def get_catalog_merge(db: Session = Depends(get_db)) -> MergeService:
    return MergeService(
        SqlAlchemyNotebookRepository(db),
        SqlAlchemyIngredientCatalog(db),
        SqlAlchemyPlaceRepository(db),
        embedding_jobs=SqlAlchemyEmbeddingJobs(db),
    )


def get_catalog_rename(db: Session = Depends(get_db)) -> RenameService:
    return RenameService(
        SqlAlchemyNotebookRepository(db),
        SqlAlchemyIngredientCatalog(db),
        SqlAlchemyPlaceRepository(db),
        embedding_jobs=SqlAlchemyEmbeddingJobs(db),
    )


def get_catalog_delete(db: Session = Depends(get_db)) -> DeleteNameService:
    return DeleteNameService(SqlAlchemyNotebookRepository(db), SqlAlchemyIngredientCatalog(db))


def get_catalog_split(db: Session = Depends(get_db)) -> SplitService:
    return SplitService(
        SqlAlchemyNotebookRepository(db),
        SqlAlchemyIngredientCatalog(db),
        embedding_jobs=SqlAlchemyEmbeddingJobs(db),
    )


def get_pair_suggester(request: Request) -> IngredientPairSuggester:
    """One per process, like the extractor; tests override this dependency."""
    cached = getattr(request.app.state, "pair_suggester", None)
    if cached is None:
        settings = load_gemini_settings()
        cached = GeminiPairSuggester(
            api_key=settings.api_key,
            model=settings.chat_model,
            timeout_s=settings.text_timeout_s,
        )
        request.app.state.pair_suggester = cached
    return cached


def get_catalog_suggest_pairs(
    db: Session = Depends(get_db),
    suggester: IngredientPairSuggester = Depends(get_pair_suggester),
) -> SuggestPairsService:
    return SuggestPairsService(
        SqlAlchemyNotebookRepository(db), SqlAlchemyIngredientCatalog(db), suggester
    )


def get_catalog_dismiss_pair(db: Session = Depends(get_db)) -> DismissPairService:
    return DismissPairService(SqlAlchemyNotebookRepository(db), SqlAlchemyIngredientCatalog(db))
