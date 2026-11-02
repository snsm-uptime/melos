"""Notebook invite use cases against fake ports (spec 057)."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from application.notebook_invites import (
    AcceptNotebookInviteCommand,
    AcceptNotebookInviteService,
    CancelNotebookInviteCommand,
    CancelNotebookInviteService,
    ListNotebookInvitesCommand,
    ListNotebookInvitesService,
    PreviewNotebookInviteCommand,
    PreviewNotebookInviteService,
    ResendNotebookInviteCommand,
    ResendNotebookInviteService,
    SendNotebookInviteCommand,
    SendNotebookInviteService,
    build_notebook_invite_email,
)
from domain.errors import (
    AlreadyInNotebookError,
    EmailNotVerifiedError,
    InvalidInviteEmailError,
    InvalidInviteTokenError,
    InviteEmailMismatchError,
    NotebookInviteNotFoundError,
    NotebookNotFoundError,
    NotebookNotShareableError,
    NotebookOwnerOnlyError,
    SmtpSendError,
)
from domain.kitchen_invite import hash_invite_token
from tests.notebook_sharing_fakes import (
    FakeCatalog,
    FakeCommitter,
    FakeInvites,
    FakeMailer,
    FakeNotebooks,
    FakePeople,
)


@dataclass
class World:
    log: list[str] = field(default_factory=list)
    notebooks: FakeNotebooks = field(init=False)
    invites: FakeInvites = field(init=False)
    catalog: FakeCatalog = field(init=False)
    committer: FakeCommitter = field(init=False)
    people: FakePeople = field(default_factory=FakePeople)
    mailer: FakeMailer = field(default_factory=FakeMailer)
    owner: UUID = field(init=False)
    notebook: UUID = field(init=False)

    def __post_init__(self) -> None:
        self.notebooks = FakeNotebooks(log=self.log)
        self.invites = FakeInvites(log=self.log)
        self.catalog = FakeCatalog(log=self.log)
        self.committer = FakeCommitter(log=self.log)
        self.owner = self.people.add("ana@example.test", alias="ana")
        self.notebook = self.notebooks.personal(self.owner)

    def send_service(self) -> SendNotebookInviteService:
        return SendNotebookInviteService(
            self.notebooks,
            self.invites,
            self.people,
            self.people,
            self.mailer,
            public_app_url="https://melos.test/",
        )

    def send(self, email: str = "ben@example.test", actor: UUID | None = None):
        return self.send_service().execute(
            SendNotebookInviteCommand(
                actor_user_id=actor or self.owner, notebook_id=self.notebook, email=email
            )
        )

    def resend_service(self) -> ResendNotebookInviteService:
        return ResendNotebookInviteService(
            self.notebooks,
            self.invites,
            self.people,
            self.people,
            self.mailer,
            public_app_url="https://melos.test/",
        )

    def accept_service(self) -> AcceptNotebookInviteService:
        return AcceptNotebookInviteService(
            self.invites,
            self.notebooks,
            self.people,
            self.people,
            self.catalog,
            self.committer,
        )

    def accept(self, token: str, actor: UUID, *, verification: bool = False):
        return self.accept_service().execute(
            AcceptNotebookInviteCommand(
                actor_user_id=actor,
                raw_token=token,
                email_verification_required=verification,
            )
        )

    def preview(self, token: str):
        return PreviewNotebookInviteService(self.invites, self.notebooks, self.people).execute(
            PreviewNotebookInviteCommand(raw_token=token)
        )

    def sent_token(self, index: int = -1) -> str:
        return self.mailer.sent[index].body_text.split("?token=")[1].split()[0]

    def only_invite(self):
        rows = list(self.invites.rows.values())
        assert len(rows) == 1
        return rows[0]

    def expire(self, invite_id: UUID) -> None:
        row = self.invites.rows[invite_id]
        self.invites.rows[invite_id] = replace(
            row, expires_at=datetime.now(UTC) - timedelta(minutes=1)
        )


@pytest.fixture
def world() -> World:
    return World()


# --- Sending -------------------------------------------------------------------------------


def test_owner_sends_and_only_the_hash_is_stored(world: World) -> None:
    result = world.send("Ben@Example.Test ")
    invite = world.only_invite()
    assert result.status == "sent"
    assert result.invite.email == "ben@example.test"
    assert result.invite.expired is False
    assert invite.invited_by == world.owner
    token = world.sent_token()
    assert invite.token_hash == hash_invite_token(token)
    assert token not in invite.token_hash
    assert world.mailer.sent[0].to_address == "ben@example.test"
    assert f"https://melos.test/invites/notebook?token={token}" in world.mailer.sent[0].body_text


def test_link_lasts_seven_days(world: World) -> None:
    world.send()
    left = world.only_invite().expires_at - datetime.now(UTC)
    assert timedelta(days=6, hours=23) < left <= timedelta(days=7)


def test_member_is_refused_as_owner_only(world: World) -> None:
    member = world.people.add("ben@example.test", alias="ben")
    world.notebooks.roles[(world.notebook, member)] = "member"
    with pytest.raises(NotebookOwnerOnlyError):
        world.send("carla@example.test", actor=member)
    assert world.mailer.sent == []


def test_stranger_gets_not_found(world: World) -> None:
    stranger = world.people.add("eve@example.test", alias="eve")
    with pytest.raises(NotebookNotFoundError):
        world.send(actor=stranger)


def test_missing_notebook_gets_not_found(world: World) -> None:
    with pytest.raises(NotebookNotFoundError):
        world.send_service().execute(
            SendNotebookInviteCommand(
                actor_user_id=world.owner, notebook_id=uuid4(), email="ben@example.test"
            )
        )


def test_kitchen_notebook_is_refused(world: World) -> None:
    notebook = world.notebooks.kitchen(world.owner)
    with pytest.raises(NotebookNotShareableError):
        world.send_service().execute(
            SendNotebookInviteCommand(
                actor_user_id=world.owner, notebook_id=notebook, email="ben@example.test"
            )
        )


def test_person_outside_a_kitchen_gets_not_found_on_its_notebook(world: World) -> None:
    notebook = world.notebooks.kitchen(uuid4())
    with pytest.raises(NotebookNotFoundError):
        world.send_service().execute(
            SendNotebookInviteCommand(
                actor_user_id=world.owner, notebook_id=notebook, email="ben@example.test"
            )
        )


def test_bad_email_stores_and_sends_nothing(world: World) -> None:
    with pytest.raises(InvalidInviteEmailError):
        world.send("not-an-email")
    assert world.invites.rows == {} and world.mailer.sent == []


def test_a_member_with_a_bad_email_gets_the_access_refusal_first(world: World) -> None:
    member = world.people.add("ben@example.test", alias="ben")
    world.notebooks.roles[(world.notebook, member)] = "member"
    with pytest.raises(NotebookOwnerOnlyError):
        world.send("not-an-email", actor=member)


def test_owner_as_invitee_is_already_in(world: World) -> None:
    with pytest.raises(AlreadyInNotebookError):
        world.send("ana@example.test")


def test_member_as_invitee_is_already_in(world: World) -> None:
    member = world.people.add("ben@example.test", alias="ben")
    world.notebooks.roles[(world.notebook, member)] = "member"
    with pytest.raises(AlreadyInNotebookError):
        world.send()
    assert world.mailer.sent == []


def test_repeat_replaces_the_earlier_invite(world: World) -> None:
    world.send()
    first = world.only_invite()
    world.send()
    assert world.only_invite().id != first.id
    assert world.log.index("lock") < world.log.index("delete_open") < world.log.index("create")


def test_result_says_nothing_about_an_account(world: World) -> None:
    unknown = world.send("nobody@example.test")
    world.people.add("ben@example.test", alias="ben")
    known = world.send("ben@example.test")
    assert set(unknown.__dataclass_fields__) == set(known.__dataclass_fields__)
    assert unknown.status == known.status
    assert world.mailer.sent[0].subject == world.mailer.sent[1].subject
    assert (
        world.mailer.sent[0].body_text.split("https")[0]
        == (world.mailer.sent[1].body_text.split("https")[0])
    )


def test_failed_email_raises_for_the_route_to_roll_back(world: World) -> None:
    world.mailer.fail = SmtpSendError()
    with pytest.raises(SmtpSendError):
        world.send()


def test_unexpected_mailer_error_becomes_a_send_error(world: World) -> None:
    world.mailer.fail = RuntimeError("boom")
    with pytest.raises(SmtpSendError):
        world.send()


def test_email_language_follows_the_inviter(world: World) -> None:
    owner = world.people.add("sol@example.test", alias="sol", language="es")
    world.notebooks.roles[(world.notebook, owner)] = "owner"
    world.send(actor=owner)
    assert "cuaderno" in world.mailer.sent[0].body_text


def _email(locale: str, name: str = "Recetas", alias: str = "ana"):
    return build_notebook_invite_email(
        to="ben@example.test",
        link="https://melos.test/invites/notebook?token=t&x=1",
        notebook_name=name,
        inviter_alias=alias,
        locale=locale,  # type: ignore[arg-type]
    )


def test_english_email_names_notebook_alias_and_days() -> None:
    message = _email("en")
    assert "Recetas" in message.subject
    assert "ana" in message.body_text and "Recetas" in message.body_text
    assert "7 days" in message.body_text
    assert "notebook" in message.body_text


def test_spanish_email_says_cuaderno_and_never_lista() -> None:
    message = _email("es")
    for text in (message.subject, message.body_text, message.body_html or ""):
        assert "cuaderno" in text.lower()
        assert "lista" not in text.lower()
    assert "7 días" in message.body_text


def test_line_breaks_leave_the_subject_and_html_is_escaped() -> None:
    message = _email("en", name="Bad\r\nBcc: x@example.test<b>", alias="a\nb")
    assert "\n" not in message.subject and "\r" not in message.subject
    assert "<b>" not in (message.body_html or "")
    assert "&lt;b&gt;" in (message.body_html or "")
    assert "token=t&amp;x=1" in (message.body_html or "")


# --- Preview -------------------------------------------------------------------------------


def test_preview_shows_only_the_safe_fields(world: World) -> None:
    world.send()
    result = world.preview(world.sent_token())
    assert result.notebook_name == "ana's Notebook"
    assert result.inviter_alias == "ana"
    assert result.email_hint == "b***n@example.test"


def test_preview_has_no_alias_once_the_sender_is_gone(world: World) -> None:
    world.send()
    invite = world.only_invite()
    world.invites.rows[invite.id] = replace(invite, invited_by=None)
    assert world.preview(world.sent_token()).inviter_alias is None


@pytest.mark.parametrize("state", ["unknown", "used", "expired"])
def test_preview_of_a_dead_link_is_invalid(world: World, state: str) -> None:
    world.send()
    invite = world.only_invite()
    token = world.sent_token()
    if state == "unknown":
        token = "nope"
    elif state == "used":
        world.invites.rows[invite.id] = replace(invite, used_at=datetime.now(UTC))
    else:
        world.expire(invite.id)
    with pytest.raises(InvalidInviteTokenError):
        world.preview(token)


# --- Accepting -----------------------------------------------------------------------------


def test_accept_joins_and_commits_once(world: World) -> None:
    ben = world.people.add("ben@example.test", alias="ben")
    world.send()
    result = world.accept(world.sent_token(), ben)
    assert result.notebook_id == world.notebook
    assert result.already_member is False
    assert world.notebooks.roles[(world.notebook, ben)] == "member"
    assert world.only_invite().used_at is not None
    assert world.committer.commits == 1


def test_accept_order_merges_after_the_claim_and_before_the_membership(world: World) -> None:
    ben = world.people.add("ben@example.test", alias="ben")
    world.send()
    world.log.clear()
    world.catalog.person[ben] = ["saffron"]
    world.accept(world.sent_token(), ben)
    assert world.log == [
        "lock",
        "claim",
        "names_for_person",
        "add_names",
        "add_member",
        "commit",
    ]


def test_merge_keeps_the_notebooks_name_and_adds_the_rest(world: World) -> None:
    ben = world.people.add("ben@example.test", alias="ben")
    world.catalog.notebook[world.notebook] = ["onion"]
    world.catalog.person[ben] = ["onions", "saffron", "tomato", "tomatoes"]
    world.send()
    world.accept(world.sent_token(), ben)
    assert world.catalog.notebook[world.notebook] == ["onion", "saffron", "tomato"]


def test_someone_already_in_gets_a_quiet_success(world: World) -> None:
    ben = world.people.add("ben@example.test", alias="ben")
    world.notebooks.roles[(world.notebook, ben)] = "member"
    world.send("ben2@example.test")
    invite = world.only_invite()
    world.invites.rows[invite.id] = replace(invite, email="ben@example.test")
    world.log.clear()
    result = world.accept(world.sent_token(), ben)
    assert result.already_member is True and result.notebook_id == world.notebook
    assert world.log == []


def test_a_used_link_is_a_quiet_success_for_someone_in_the_notebook(world: World) -> None:
    ben = world.people.add("ben@example.test", alias="ben")
    world.send()
    token = world.sent_token()
    world.accept(token, ben)
    assert world.accept(token, ben).already_member is True
    assert world.committer.commits == 1


def test_live_link_for_another_email_is_a_mismatch_and_stays_usable(world: World) -> None:
    ben = world.people.add("ben@example.test", alias="ben")
    carla = world.people.add("carla@example.test", alias="carla")
    world.send()
    token = world.sent_token()
    with pytest.raises(InviteEmailMismatchError):
        world.accept(token, carla)
    assert world.only_invite().used_at is None
    assert world.accept(token, ben).already_member is False


def test_expired_link_for_another_email_is_invalid_not_a_mismatch(world: World) -> None:
    carla = world.people.add("carla@example.test", alias="carla")
    world.send()
    world.expire(world.only_invite().id)
    with pytest.raises(InvalidInviteTokenError):
        world.accept(world.sent_token(), carla)


def test_used_link_for_another_email_is_invalid_not_a_mismatch(world: World) -> None:
    ben = world.people.add("ben@example.test", alias="ben")
    carla = world.people.add("carla@example.test", alias="carla")
    world.send()
    token = world.sent_token()
    world.accept(token, ben)
    with pytest.raises(InvalidInviteTokenError):
        world.accept(token, carla)


def test_a_removed_member_cannot_reuse_their_link(world: World) -> None:
    ben = world.people.add("ben@example.test", alias="ben")
    world.send()
    token = world.sent_token()
    world.accept(token, ben)
    del world.notebooks.roles[(world.notebook, ben)]
    with pytest.raises(InvalidInviteTokenError):
        world.accept(token, ben)


def test_expired_link_is_invalid(world: World) -> None:
    ben = world.people.add("ben@example.test", alias="ben")
    world.send()
    world.expire(world.only_invite().id)
    with pytest.raises(InvalidInviteTokenError):
        world.accept(world.sent_token(), ben)


def test_unknown_token_is_invalid(world: World) -> None:
    ben = world.people.add("ben@example.test", alias="ben")
    with pytest.raises(InvalidInviteTokenError):
        world.accept("nope", ben)


def test_unverified_email_stops_and_leaves_the_invite_usable(world: World) -> None:
    ben = world.people.add("ben@example.test", alias="ben")
    world.send()
    token = world.sent_token()
    with pytest.raises(EmailNotVerifiedError):
        world.accept(token, ben, verification=True)
    assert world.only_invite().used_at is None
    assert (world.notebook, ben) not in world.notebooks.roles
    world.people.verified[ben] = datetime.now(UTC)
    assert world.accept(token, ben, verification=True).already_member is False


def test_lost_claim_with_a_membership_succeeds(world: World) -> None:
    ben = world.people.add("ben@example.test", alias="ben")
    world.send()

    def winner() -> None:
        world.notebooks.roles[(world.notebook, ben)] = "member"

    world.invites.lose_next_claim_to = winner
    world.catalog.person[ben] = ["saffron"]
    result = world.accept(world.sent_token(), ben)
    assert result.already_member is True
    assert world.catalog.notebook.get(world.notebook) is None


def test_lost_claim_without_a_membership_is_invalid(world: World) -> None:
    ben = world.people.add("ben@example.test", alias="ben")
    world.send()
    world.invites.lose_next_claim_to = lambda: None
    with pytest.raises(InvalidInviteTokenError):
        world.accept(world.sent_token(), ben)


# --- The owner's list, resend and cancel (User Story 5) ------------------------------------


def test_accept_answers_as_an_invalid_link_when_the_notebook_was_just_deleted(world: World) -> None:
    ben = world.people.add("ben@example.test", alias="ben")
    world.send()
    del world.notebooks.notebooks[world.notebook]

    with pytest.raises(InvalidInviteTokenError):
        world.accept(world.sent_token(), ben)

    assert world.committer.commits == 0
    assert "add_member" not in world.log


def _list(world: World, actor: UUID):
    return ListNotebookInvitesService(world.notebooks, world.invites).execute(
        ListNotebookInvitesCommand(actor_user_id=actor, notebook_id=world.notebook)
    )


def _resend(world: World, invite_id: UUID, actor: UUID | None = None):
    return world.resend_service().execute(
        ResendNotebookInviteCommand(
            actor_user_id=actor or world.owner, notebook_id=world.notebook, invite_id=invite_id
        )
    )


def _cancel(world: World, invite_id: UUID, actor: UUID | None = None) -> None:
    CancelNotebookInviteService(world.notebooks, world.invites).execute(
        CancelNotebookInviteCommand(
            actor_user_id=actor or world.owner, notebook_id=world.notebook, invite_id=invite_id
        )
    )


def test_owner_lists_open_and_expired_invites(world: World) -> None:
    world.send("ben@example.test")
    expired_id = world.only_invite().id
    world.expire(expired_id)
    world.send("carla@example.test")
    rows = _list(world, world.owner)
    assert [(row.email, row.expired) for row in rows] == [
        ("carla@example.test", False),
        ("ben@example.test", True),
    ]


def test_list_leaves_out_accepted_invites(world: World) -> None:
    ben = world.people.add("ben@example.test", alias="ben")
    world.send()
    world.accept(world.sent_token(), ben)
    assert _list(world, world.owner) == []


def test_member_may_not_list_invites(world: World) -> None:
    member = world.people.add("ben@example.test", alias="ben")
    world.notebooks.roles[(world.notebook, member)] = "member"
    with pytest.raises(NotebookOwnerOnlyError):
        _list(world, member)


@pytest.mark.parametrize("expired", [False, True])
def test_resend_rotates_the_same_row_for_seven_days(world: World, expired: bool) -> None:
    world.send()
    before = world.only_invite()
    if expired:
        world.expire(before.id)
    result = _resend(world, before.id)
    after = world.only_invite()
    assert after.id == before.id
    assert after.token_hash != before.token_hash
    assert after.expires_at - datetime.now(UTC) > timedelta(days=6, hours=23)
    assert result.invite.expired is False
    assert len(world.mailer.sent) == 2
    assert after.token_hash == hash_invite_token(world.sent_token())


def test_resend_records_who_resent(world: World) -> None:
    world.send()
    invite = world.only_invite()
    world.invites.rows[invite.id] = replace(invite, invited_by=None)
    _resend(world, invite.id)
    assert world.only_invite().invited_by == world.owner


def test_resend_refuses_a_person_now_in_the_notebook(world: World) -> None:
    world.send()
    ben = world.people.add("ben@example.test", alias="ben")
    world.notebooks.roles[(world.notebook, ben)] = "member"
    with pytest.raises(AlreadyInNotebookError):
        _resend(world, world.only_invite().id)


def test_resend_and_cancel_refuse_an_accepted_invite(world: World) -> None:
    ben = world.people.add("ben@example.test", alias="ben")
    world.send()
    world.accept(world.sent_token(), ben)
    invite_id = world.only_invite().id
    with pytest.raises(NotebookInviteNotFoundError):
        _resend(world, invite_id)
    with pytest.raises(NotebookInviteNotFoundError):
        _cancel(world, invite_id)


def test_cancel_ends_the_invite(world: World) -> None:
    world.send()
    _cancel(world, world.only_invite().id)
    assert world.invites.rows == {}


def test_another_notebooks_invite_id_is_not_found(world: World) -> None:
    other = world.notebooks.personal(world.owner, "Other")
    world.send_service().execute(
        SendNotebookInviteCommand(
            actor_user_id=world.owner, notebook_id=other, email="ben@example.test"
        )
    )
    invite_id = world.only_invite().id
    with pytest.raises(NotebookInviteNotFoundError):
        _resend(world, invite_id)
    with pytest.raises(NotebookInviteNotFoundError):
        _cancel(world, invite_id)


def test_member_may_not_resend_or_cancel(world: World) -> None:
    member = world.people.add("carla@example.test", alias="carla")
    world.notebooks.roles[(world.notebook, member)] = "member"
    world.send()
    invite_id = world.only_invite().id
    with pytest.raises(NotebookOwnerOnlyError):
        _resend(world, invite_id, actor=member)
    with pytest.raises(NotebookOwnerOnlyError):
        _cancel(world, invite_id, actor=member)
    assert len(world.mailer.sent) == 1
