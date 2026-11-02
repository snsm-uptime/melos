"""Sharing a personal notebook by email invite (spec 057).

Token, expiry and email rules are the kitchen invite's (research R1). What differs: one link and
one email for everyone, so nothing says whether an address has an account (R5), and accepting
merges the person's names in one transaction (R4).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from html import escape
from uuid import UUID, uuid4

from domain.errors import (
    AliasRequiredError,
    AlreadyInNotebookError,
    InvalidInviteTokenError,
    InviteEmailMismatchError,
    NotebookInviteNotFoundError,
    NotebookNotFoundError,
    SmtpConfigurationError,
    SmtpSendError,
)
from domain.ingredient_catalog import names_to_add
from domain.kitchen_invite import (
    INVITE_TOKEN_TTL,
    InviteLocale,
    assert_invite_email_bind,
    assert_invite_token_redeemable,
    generate_raw_invite_token,
    hash_invite_token,
    invite_email_hint,
    resolve_invite_locale,
    validate_invite_email,
)
from domain.notebook import Notebook, NotebookAccess, notebook_access
from domain.notebook_invite import assert_can_manage_sharing, build_notebook_invite_link

from application.email_verification import (
    EmailVerificationRepository,
    EnsureEmailVerifiedCommand,
    EnsureEmailVerifiedService,
)
from application.kitchen_invite import _safe_header_text
from application.ports import (
    EmailMessage,
    EmailSender,
    IngredientCatalog,
    NotebookInviteRecord,
    NotebookInviteRepository,
    NotebookRepository,
    PreferencesRepository,
    TransactionCommitter,
)
from application.signin import AuthUserRepository


def visible_notebook(
    notebooks: NotebookRepository, user_id: UUID, notebook_id: UUID
) -> tuple[Notebook, NotebookAccess]:
    """The notebook and the caller's access; anyone who may not see it gets "not found"."""
    facts = notebooks.facts_for(user_id, notebook_id)
    if facts is None:
        raise NotebookNotFoundError()
    access = notebook_access(facts.notebook.kind, facts.role, facts.in_kitchen)
    if access is None:
        raise NotebookNotFoundError()
    return facts.notebook, access


def _manageable_notebook(
    notebooks: NotebookRepository, user_id: UUID, notebook_id: UUID
) -> Notebook:
    notebook, access = visible_notebook(notebooks, user_id, notebook_id)
    assert_can_manage_sharing(notebook.kind, access)
    return notebook


def build_notebook_invite_email(
    *,
    to: str,
    link: str,
    notebook_name: str,
    inviter_alias: str,
    locale: InviteLocale,
) -> EmailMessage:
    """One template per language, for people with and without an account (research R5)."""
    name = _safe_header_text(notebook_name)
    inviter = _safe_header_text(inviter_alias)
    name_html = escape(name)
    inviter_html = escape(inviter)
    href = escape(link, quote=True)
    days = INVITE_TOKEN_TTL.days

    if locale == "es":
        subject = f"Invitación al cuaderno {name}"
        invited = "te invitó al cuaderno"
        quoted, quoted_html = f"«{name}»", f"«{name_html}»"
        place = "en Melos."
        open_line = f"Abre este enlace para unirte (válido {days} días):"
        account = "Si aún no tienes cuenta, el enlace te lleva a crear una con este correo."
        cta = "Abrir el cuaderno"
        ignore = "Si no esperabas esta invitación, puedes ignorar este correo."
    else:
        subject = f"Invitation to the notebook {name}"
        invited = "invited you to the notebook"
        quoted, quoted_html = f"“{name}”", f"“{name_html}”"
        place = "on Melos."
        open_line = f"Open this link to join (valid for {days} days):"
        account = "If you don’t have an account yet, the link helps you create one with this email."
        cta = "Open the notebook"
        ignore = "If you weren’t expecting this, you can ignore this email."

    return EmailMessage(
        to_address=to,
        subject=subject,
        body_text=(
            f"{inviter} {invited} {quoted} {place}\n\n"
            f"{open_line}\n{link}\n\n{account}\n\n{ignore}\n"
        ),
        body_html=(
            f"<p>{inviter_html} {invited} {quoted_html} {place}</p>"
            f"<p>{open_line}</p>"
            f'<p><a href="{href}">{cta}</a></p>'
            f"<p>{account}</p>"
            f"<p>{ignore}</p>"
        ),
    )


def _assert_not_in_notebook(
    notebooks: NotebookRepository, users: AuthUserRepository, notebook_id: UUID, email: str
) -> None:
    person = users.get_by_email(email)
    if person is not None and notebooks.role_of(notebook_id, person.id) is not None:
        raise AlreadyInNotebookError()


@dataclass(frozen=True, slots=True)
class NotebookInviteView:
    id: UUID
    email: str
    expires_at: datetime
    expired: bool


def _view(
    invite_id: UUID, email: str, expires_at: datetime, *, now: datetime
) -> NotebookInviteView:
    return NotebookInviteView(
        id=invite_id, email=email, expires_at=expires_at, expired=expires_at <= now
    )


@dataclass(frozen=True, slots=True)
class NotebookInviteSent:
    status: str  # "sent"
    invite: NotebookInviteView


class _InviteMail:
    """Writes the emailed link: the name and alias, the language, and a loud SMTP failure."""

    def __init__(
        self, prefs: PreferencesRepository, mailer: EmailSender, public_app_url: str
    ) -> None:
        self._prefs = prefs
        self._mailer = mailer
        self._public_app_url = public_app_url

    def send(self, *, actor_user_id: UUID, notebook: Notebook, email: str, raw_token: str) -> None:
        inviter = self._prefs.get_preferences(actor_user_id)
        if inviter is None or not inviter.alias:
            raise AliasRequiredError()
        message = build_notebook_invite_email(
            to=email,
            link=build_notebook_invite_link(self._public_app_url, raw_token),
            notebook_name=notebook.name,
            inviter_alias=inviter.alias,
            locale=resolve_invite_locale(inviter.language),
        )
        try:
            self._mailer.send(message)
        except (SmtpConfigurationError, SmtpSendError):
            raise
        except Exception as exc:
            raise SmtpSendError(
                "Could not send email. Check SMTP connectivity and try again."
            ) from exc


@dataclass(frozen=True, slots=True)
class SendNotebookInviteCommand:
    actor_user_id: UUID
    notebook_id: UUID
    email: str


class SendNotebookInviteService:
    """The owner invites an address. The route rolls back on an SMTP error (research R7)."""

    def __init__(
        self,
        notebooks: NotebookRepository,
        invites: NotebookInviteRepository,
        users: AuthUserRepository,
        prefs: PreferencesRepository,
        mailer: EmailSender,
        *,
        public_app_url: str,
    ) -> None:
        self._notebooks = notebooks
        self._invites = invites
        self._users = users
        self._mail = _InviteMail(prefs, mailer, public_app_url)

    def execute(self, command: SendNotebookInviteCommand) -> NotebookInviteSent:
        # Access first: someone who may not invite learns nothing about what they typed.
        notebook = _manageable_notebook(self._notebooks, command.actor_user_id, command.notebook_id)
        email = validate_invite_email(command.email)
        _assert_not_in_notebook(self._notebooks, self._users, notebook.id, email)

        raw = generate_raw_invite_token()
        now = datetime.now(UTC)
        expires_at = now + INVITE_TOKEN_TTL
        invite_id = uuid4()

        self._notebooks.lock_notebook(notebook.id)
        self._invites.delete_open_for_email(notebook.id, email)
        self._invites.create(
            invite_id=invite_id,
            notebook_id=notebook.id,
            email=email,
            token_hash=hash_invite_token(raw),
            invited_by=command.actor_user_id,
            expires_at=expires_at,
        )
        self._mail.send(
            actor_user_id=command.actor_user_id, notebook=notebook, email=email, raw_token=raw
        )
        return NotebookInviteSent(
            status="sent", invite=_view(invite_id, email, expires_at, now=now)
        )


@dataclass(frozen=True, slots=True)
class ResendNotebookInviteCommand:
    actor_user_id: UUID
    notebook_id: UUID
    invite_id: UUID


class ResendNotebookInviteService:
    """A new link on the same row for an open or expired invite (FR-023)."""

    def __init__(
        self,
        notebooks: NotebookRepository,
        invites: NotebookInviteRepository,
        users: AuthUserRepository,
        prefs: PreferencesRepository,
        mailer: EmailSender,
        *,
        public_app_url: str,
    ) -> None:
        self._notebooks = notebooks
        self._invites = invites
        self._users = users
        self._mail = _InviteMail(prefs, mailer, public_app_url)

    def execute(self, command: ResendNotebookInviteCommand) -> NotebookInviteSent:
        notebook = _manageable_notebook(self._notebooks, command.actor_user_id, command.notebook_id)
        self._notebooks.lock_notebook(notebook.id)
        invite = self._invites.get(notebook.id, command.invite_id)
        if invite is None or invite.used_at is not None:
            raise NotebookInviteNotFoundError()
        _assert_not_in_notebook(self._notebooks, self._users, notebook.id, invite.email)

        raw = generate_raw_invite_token()
        now = datetime.now(UTC)
        expires_at = now + INVITE_TOKEN_TTL
        self._invites.rotate(
            invite.id,
            token_hash=hash_invite_token(raw),
            invited_by=command.actor_user_id,
            expires_at=expires_at,
        )
        self._mail.send(
            actor_user_id=command.actor_user_id,
            notebook=notebook,
            email=invite.email,
            raw_token=raw,
        )
        return NotebookInviteSent(
            status="sent", invite=_view(invite.id, invite.email, expires_at, now=now)
        )


@dataclass(frozen=True, slots=True)
class CancelNotebookInviteCommand:
    actor_user_id: UUID
    notebook_id: UUID
    invite_id: UUID


class CancelNotebookInviteService:
    """Deletes an unused invite, so its link fails like an unknown one (research R2)."""

    def __init__(self, notebooks: NotebookRepository, invites: NotebookInviteRepository) -> None:
        self._notebooks = notebooks
        self._invites = invites

    def execute(self, command: CancelNotebookInviteCommand) -> None:
        notebook = _manageable_notebook(self._notebooks, command.actor_user_id, command.notebook_id)
        if not self._invites.delete(notebook.id, command.invite_id):
            raise NotebookInviteNotFoundError()


@dataclass(frozen=True, slots=True)
class ListNotebookInvitesCommand:
    actor_user_id: UUID
    notebook_id: UUID


class ListNotebookInvitesService:
    """The owner's list: open and expired invites, never the accepted ones (FR-022)."""

    def __init__(self, notebooks: NotebookRepository, invites: NotebookInviteRepository) -> None:
        self._notebooks = notebooks
        self._invites = invites

    def execute(self, command: ListNotebookInvitesCommand) -> list[NotebookInviteView]:
        notebook = _manageable_notebook(self._notebooks, command.actor_user_id, command.notebook_id)
        now = datetime.now(UTC)
        return [
            _view(row.id, row.email, row.expires_at, now=now)
            for row in self._invites.list_unused(notebook.id)
        ]


@dataclass(frozen=True, slots=True)
class PreviewNotebookInviteCommand:
    raw_token: str


@dataclass(frozen=True, slots=True)
class NotebookInvitePreview:
    notebook_name: str
    inviter_alias: str | None
    email_hint: str


class PreviewNotebookInviteService:
    """What a signed-out visitor sees. Every dead link fails the same way (FR-014, SC-006)."""

    def __init__(
        self,
        invites: NotebookInviteRepository,
        notebooks: NotebookRepository,
        prefs: PreferencesRepository,
    ) -> None:
        self._invites = invites
        self._notebooks = notebooks
        self._prefs = prefs

    def execute(self, command: PreviewNotebookInviteCommand) -> NotebookInvitePreview:
        invite = self._invites.get_by_token_hash(hash_invite_token(command.raw_token))
        if invite is None:
            raise InvalidInviteTokenError()
        assert_invite_token_redeemable(
            used_at=invite.used_at, expires_at=invite.expires_at, now=datetime.now(UTC)
        )
        notebook = self._notebooks.get(invite.notebook_id)
        if notebook is None:
            raise InvalidInviteTokenError()
        return NotebookInvitePreview(
            notebook_name=notebook.name,
            inviter_alias=self._alias(invite),
            email_hint=invite_email_hint(invite.email),
        )

    def _alias(self, invite: NotebookInviteRecord) -> str | None:
        if invite.invited_by is None:
            return None
        sender = self._prefs.get_preferences(invite.invited_by)
        return sender.alias if sender is not None else None


@dataclass(frozen=True, slots=True)
class AcceptNotebookInviteCommand:
    actor_user_id: UUID
    raw_token: str
    email_verification_required: bool


@dataclass(frozen=True, slots=True)
class AcceptNotebookInviteResult:
    notebook_id: UUID
    already_member: bool


class AcceptNotebookInviteService:
    """Joins the invited person, in the order of research R4.

    All or nothing (FR-015): the route rolls back on every error. The merge reads the person's
    names before the membership exists, so the notebook's own names aren't counted as theirs.
    Committing here means the notebook is visible before the ui opens it.
    """

    def __init__(
        self,
        invites: NotebookInviteRepository,
        notebooks: NotebookRepository,
        users: AuthUserRepository,
        verification: EmailVerificationRepository,
        catalog: IngredientCatalog,
        committer: TransactionCommitter,
    ) -> None:
        self._invites = invites
        self._notebooks = notebooks
        self._users = users
        self._verification = verification
        self._catalog = catalog
        self._committer = committer

    def execute(self, command: AcceptNotebookInviteCommand) -> AcceptNotebookInviteResult:
        user_id = command.actor_user_id
        invite = self._invites.get_by_token_hash(hash_invite_token(command.raw_token))
        actor = self._users.get_by_id(user_id)
        if invite is None or actor is None:
            raise InvalidInviteTokenError()
        now = datetime.now(UTC)
        notebook_id = invite.notebook_id

        try:
            assert_invite_email_bind(invitee_email=invite.email, actor_email=actor.email)
        except InviteEmailMismatchError:
            # A dead link reveals nothing, so it can't answer "this is for someone else".
            assert_invite_token_redeemable(
                used_at=invite.used_at, expires_at=invite.expires_at, now=now
            )
            raise

        if self._notebooks.role_of(notebook_id, user_id) is not None:
            return AcceptNotebookInviteResult(notebook_id=notebook_id, already_member=True)

        assert_invite_token_redeemable(
            used_at=invite.used_at, expires_at=invite.expires_at, now=now
        )
        EnsureEmailVerifiedService(self._verification).execute(
            EnsureEmailVerifiedCommand(
                user_id=user_id,
                email_verification_required=command.email_verification_required,
            )
        )

        # A second request waits here, so its claim fails after the first has committed.
        self._notebooks.lock_notebook(notebook_id)
        if not self._invites.claim(invite.id, used_at=now):
            if self._notebooks.role_of(notebook_id, user_id) is not None:
                return AcceptNotebookInviteResult(notebook_id=notebook_id, already_member=True)
            raise InvalidInviteTokenError()

        new_names = names_to_add(
            self._catalog.names_for_person(user_id),
            self._catalog.names_for_notebook(notebook_id),
        )
        self._catalog.add_names(notebook_id, new_names)
        self._notebooks.add_member(notebook_id, user_id)
        self._committer.commit()
        return AcceptNotebookInviteResult(notebook_id=notebook_id, already_member=False)
