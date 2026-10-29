"""Domain errors for account and kitchen operations."""

from uuid import UUID


class DomainError(Exception):
    """Base domain error."""


class DuplicateEmailError(DomainError):
    """Raised when signup email is already registered."""


class InvalidSignupError(DomainError):
    """Raised when signup input fails validation."""


class InvalidCredentialsError(DomainError):
    """Raised for any failed sign-in — never distinguish unknown email vs bad password."""

    MESSAGE = "Invalid email or password."

    def __init__(self) -> None:
        super().__init__(self.MESSAGE)


class RateLimitedError(DomainError):
    """Raised when an auth request path exceeds its configured rate limit."""

    MESSAGE = "Too many attempts. Please try again later."
    CODE = "rate_limited"

    def __init__(self) -> None:
        super().__init__(self.MESSAGE)


class InvalidResetTokenError(DomainError):
    """Raised when a password-reset token is missing, expired, or already used."""

    MESSAGE = "This reset link is invalid or has expired. Request a new one."

    def __init__(self) -> None:
        super().__init__(self.MESSAGE)


class InvalidResetPasswordError(DomainError):
    """Raised when the new password fails validation on reset confirm."""

    MESSAGE = "Password must be at least 8 characters."

    def __init__(self, detail: str | None = None) -> None:
        super().__init__(detail or self.MESSAGE)


class SmtpConfigurationError(DomainError):
    """Raised when SMTP is missing or misconfigured (operator-facing)."""

    MESSAGE = "Email delivery is not configured. Check SMTP settings."

    def __init__(self, detail: str | None = None) -> None:
        super().__init__(detail or self.MESSAGE)


class SmtpSendError(DomainError):
    """Raised when SMTP is configured but send fails (no silent success)."""

    MESSAGE = "Could not send email. Check SMTP connectivity and try again."

    def __init__(self, detail: str | None = None) -> None:
        super().__init__(detail or self.MESSAGE)


class EmailNotVerifiedError(DomainError):
    """Raised when a gated flow requires verified email and the user is unverified."""

    MESSAGE = (
        "Verify your email before continuing with this action. "
        "Check your inbox for a verification link, or open /verify to resend one."
    )

    def __init__(self) -> None:
        super().__init__(self.MESSAGE)


class InvalidVerificationTokenError(DomainError):
    """Raised when an email-verification token is missing, expired, or already used."""

    MESSAGE = "This verification link is invalid or has expired. Request a new one."

    def __init__(self) -> None:
        super().__init__(self.MESSAGE)


class VerificationNotRequiredError(DomainError):
    """Raised when verification endpoints are called while the config gate is off."""

    MESSAGE = "Email verification is not required for this deployment."

    def __init__(self) -> None:
        super().__init__(self.MESSAGE)


class PrincipalNotFoundError(DomainError):
    """Raised when an authenticated user_id has no matching account row."""

    MESSAGE = "Not authenticated."

    def __init__(self) -> None:
        super().__init__(self.MESSAGE)


class InvalidPreferencesError(DomainError):
    """Raised when language/theme preference values are invalid."""

    MESSAGE = "Invalid preference value."

    def __init__(self, detail: str | None = None) -> None:
        super().__init__(detail or self.MESSAGE)


class InvalidAliasError(DomainError):
    """Raised when an alias fails length/charset validation."""

    MESSAGE = "Alias must be 3-32 characters using lowercase letters, numbers, and underscores."
    CODE = "invalid_alias"

    def __init__(self, detail: str | None = None) -> None:
        super().__init__(detail or self.MESSAGE)


class AliasTakenError(DomainError):
    """Raised when the requested alias is already claimed (case-insensitive)."""

    MESSAGE = "That alias is taken. Try another one."
    CODE = "alias_taken"

    def __init__(self) -> None:
        super().__init__(self.MESSAGE)


class AliasAlreadySetError(DomainError):
    """Raised when an account with an alias attempts to change it (rename is deferred)."""

    MESSAGE = "Your alias is already set and cannot be changed yet."
    CODE = "alias_already_set"

    def __init__(self) -> None:
        super().__init__(self.MESSAGE)


class InvalidPhotoError(DomainError):
    """Raised when a profile photo payload fails prefix/size validation."""

    MESSAGE = "Photo must be a data:image/png or data:image/jpeg base64 string under 300KB."
    CODE = "invalid_photo"

    def __init__(self, detail: str | None = None) -> None:
        super().__init__(detail or self.MESSAGE)


class AliasRequiredError(DomainError):
    """Raised when an authenticated user without an alias touches kitchen surfaces."""

    MESSAGE = "Choose an alias before using kitchens."
    CODE = "alias_required"

    def __init__(self) -> None:
        super().__init__(self.MESSAGE)


class InvalidKitchenNameError(DomainError):
    """Raised when a kitchen name is empty or whitespace-only."""

    MESSAGE = "Enter a kitchen name."

    def __init__(self, detail: str | None = None) -> None:
        super().__init__(detail or self.MESSAGE)


class KitchenNotFoundError(DomainError):
    """Raised when a kitchen id does not exist."""

    MESSAGE = "Kitchen not found."

    def __init__(self) -> None:
        super().__init__(self.MESSAGE)


class NotKitchenMemberError(DomainError):
    """Raised when the actor is not a member of the kitchen (ACL)."""

    MESSAGE = "You do not have access to this kitchen."

    def __init__(self) -> None:
        super().__init__(self.MESSAGE)


class NotKitchenOwnerError(DomainError):
    """Raised when a member who is not the owner attempts an owner-only action."""

    MESSAGE = "Only the kitchen owner can perform this action."

    def __init__(self, detail: str | None = None) -> None:
        super().__init__(detail or self.MESSAGE)


class KitchenWriteError(DomainError):
    """Raised when kitchen persistence fails due to a constraint / integrity error."""

    MESSAGE = "Could not create the kitchen. Try again."

    def __init__(self, detail: str | None = None) -> None:
        super().__init__(detail or self.MESSAGE)


class InvalidNotebookError(DomainError):
    """Raised when a notebook breaks its invariants (for example a blank name)."""

    MESSAGE = "A notebook needs a name, and only a kitchen notebook has an origin or an owner."

    def __init__(self) -> None:
        super().__init__(self.MESSAGE)


class NotebookNotFoundError(DomainError):
    """Raised for a missing notebook and for a notebook the caller may not see — same body."""

    MESSAGE = "Notebook not found."
    CODE = "notebook_not_found"

    def __init__(self) -> None:
        super().__init__(self.MESSAGE)


class KitchenArchivedError(DomainError):
    """Raised when a capture is attempted in an archived kitchen (spec 016 FR-033)."""

    MESSAGE = "This kitchen is archived, so recipes can't be added."
    CODE = "kitchen_archived"

    def __init__(self) -> None:
        super().__init__(self.MESSAGE)


class NotebookChoiceRequiredError(DomainError):
    """Raised when a capture has several candidate notebooks and no pick."""

    MESSAGE = "Choose a notebook for this recipe."
    CODE = "notebook_choice_required"

    def __init__(self, candidate_ids: list[UUID]) -> None:
        super().__init__(self.MESSAGE)
        self.candidate_ids = candidate_ids


class RecipeNotFoundError(DomainError):
    """Raised for a missing recipe and for one in a notebook the caller may not see — same body."""

    MESSAGE = "That recipe isn't available."
    CODE = "recipe_not_found"

    def __init__(self) -> None:
        super().__init__(self.MESSAGE)


class RecipeReadOnlyError(DomainError):
    """Raised when the caller may read a recipe but not change or delete it (spec 027 FR-006)."""

    MESSAGE = "You can only read this recipe."
    CODE = "recipe_read_only"

    def __init__(self) -> None:
        super().__init__(self.MESSAGE)


class RecipeChangedError(DomainError):
    """Raised when a recipe changed after the caller opened it (spec 027 FR-011)."""

    MESSAGE = "This recipe was changed after you opened it."
    CODE = "recipe_changed"

    def __init__(self) -> None:
        super().__init__(self.MESSAGE)


class InvalidInviteEmailError(DomainError):
    """Raised when an invite email fails shape validation."""

    MESSAGE = "Enter a valid email address."

    def __init__(self, detail: str | None = None) -> None:
        super().__init__(detail or self.MESSAGE)


class AlreadyKitchenMemberError(DomainError):
    """Raised when inviting an email that already has membership on the kitchen."""

    MESSAGE = "That person is already a member of this kitchen."

    def __init__(self) -> None:
        super().__init__(self.MESSAGE)


class InvalidInviteTokenError(DomainError):
    """Raised when an invite token is missing, expired, or already used."""

    MESSAGE = "This invite link is invalid or has expired. Ask the kitchen owner for a new invite."
    CODE = "invalid_invite_token"

    def __init__(self) -> None:
        super().__init__(self.MESSAGE)


class InviteEmailMismatchError(DomainError):
    """Raised when signup/accept email does not match the invitee on the token."""

    MESSAGE = "Use the email address this invite was sent to."
    CODE = "invite_email_mismatch"

    def __init__(self) -> None:
        super().__init__(self.MESSAGE)


class InvalidPageError(DomainError):
    """Raised when a recipe list asks for a page below 1 (spec 021)."""

    MESSAGE = "Page numbers start at 1."
    CODE = "invalid_page"

    def __init__(self) -> None:
        super().__init__(self.MESSAGE)


class CartLockedError(DomainError):
    """Raised when another live session edits the kitchen's cart (spec 022 FR-017)."""

    MESSAGE = "{alias} is editing the cart."
    CODE = "cart_locked"

    def __init__(self, editor_alias: str | None) -> None:
        super().__init__(self.MESSAGE.format(alias=editor_alias or "unknown"))
        self.editor_alias = editor_alias


class RecipeLockedError(DomainError):
    """Raised when another live session edits the recipe (spec 022 FR-022)."""

    MESSAGE = "{alias} is editing this recipe."
    CODE = "recipe_locked"

    def __init__(self, editor_alias: str | None) -> None:
        super().__init__(self.MESSAGE.format(alias=editor_alias or "unknown"))
        self.editor_alias = editor_alias


class NotEditingError(DomainError):
    """Raised when a draft write, save or recipe edit comes without a live lock (spec 022)."""

    MESSAGE = "You are not editing this."
    CODE = "not_editing"

    def __init__(self) -> None:
        super().__init__(self.MESSAGE)


class CartValueError(DomainError):
    """Raised when people or meals is not a whole number from 1 to 99, or a recipe repeats."""

    MESSAGE = "Enter a whole number from 1 to 99."
    CODE = "invalid_value"

    def __init__(self, field: str) -> None:
        super().__init__(self.MESSAGE)
        self.field = field
