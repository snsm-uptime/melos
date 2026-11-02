# Research: Share a notebook by email invite

**Feature**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

## R1. Reuse of the kitchen invite

- **Decision**: Import the pure rules from `domain/kitchen_invite.py` (token generation and hash, `INVITE_TOKEN_TTL`, `validate_invite_email`, `resolve_invite_locale`, `assert_invite_token_redeemable`, `assert_invite_email_bind`, `invite_email_hint`) and `claim_single_use_email_token`. Write new services, routes and email text.
- **Rationale**: These rules are what the spec means by "reuses the flow". The kitchen services are tied to kitchen ids, kitchen text and signup-with-invite.
- **Alternatives considered**: One generic invite table and service. That would touch working kitchen code and migrate its data the day before delivery, and PRD §1.6 already lists a separate table.

## R2. Invite storage

- **Decision**: A new `notebook_invite` table. Sending, resending and replacing work as follows:
  - Cancelling or replacing an invite **deletes its row**.
  - Resending rewrites the token and expiry on the same row.
  - A partial unique index allows one unused row per notebook and email.
  - The usage column is `used_at`, not the PRD's `accepted_at`, because `claim_single_use_email_token` expects that name. PRD §1.6 gets the same wording.
- **Rationale**: A deleted row fails the same way as an unknown token, so cancelled and replaced links can't reveal anything (SC-006). A mistyped address also leaves the database. The owner's list is then simply the unused rows, with no status column.
- **Alternatives considered**: Marking old rows as used, as kitchen invites do. It needs a status column to tell cancelled from accepted, and keeps addresses for no purpose.

## R3. Who sent the invite

- **Decision**: `invited_by` is nullable, with `ON DELETE SET NULL`.
- **Rationale**: An invite belongs to the notebook and outlives the sender (spec edge case, S-058). The kitchen table cascades instead, so it can't be copied here. With no sender, the preview leaves out the inviter's alias.

## R4. Accepting: order and transaction

- **Decision**: `POST /invites/notebook/accept` runs these steps:
  1. Find the token. No row answers invalid.
  2. Check the email. On a mismatch, answer invalid if the invite can't be redeemed, otherwise answer mismatch.
  3. If the caller is already in the notebook, return success and change nothing.
  4. Check that the token can be redeemed, then that the email is verified.
  5. Lock the notebook row.
  6. Claim the token. If the claim fails and the caller is now a member, return success; otherwise answer invalid.
  7. Read the person's names, merge them, and add the membership.
  8. Commit, then respond.
- **Rationale**:
  - The atomic claim makes one membership and one merge, because a second request blocks until the first commits (FR-015).
  - The personal names are read before the membership exists, so the target's own names are not counted (FR-017).
  - The kitchen flow checks the email first, so a used link can still answer "mismatch". The notebook flow doesn't, because a dead link must reveal nothing (SC-006).
- **Two differences from the kitchen route, both needed**:
  - `get_db` commits after a route returns normally, even when the route returns an error response. So every error branch of the accept route calls `db.rollback()`, or a claimed token could be committed without a membership (SC-007).
  - The service commits through `TransactionCommitter` before returning, so the ui can't open the notebook before the membership is visible.

## R5. One link and one email for everyone

- **Decision**: Every invite links to `/invites/notebook?token=…`. There is one email template per language, and the preview has no `path` field. A signed-out visitor always sees both Sign in and Create account.
- **Rationale**: The kitchen flow picks a join or signup link from whether the address has an account, and its response and preview show that choice. FR-009 forbids that here for the owner, and the same reasoning holds for anyone holding the link. The owner's confirmation is a plain `sent`.
- **Alternatives considered**: Reusing the two kitchen templates. It would need `template_kind` removed from the response anyway, and the signup link would lead into the auth route.

## R6. Merge rule

- **Decision**: A new pure function, `names_to_add(incoming, existing)`, in `domain/ingredient_catalog.py`. It keeps the rule of `match_line`: two names match when one's key is among the other's `singular_forms`. It works in sorted order and adds each accepted name to the known set, so "tomato" and "tomatoes" add one name (FR-018).
- **Rationale**: Calling `propose_entry` for each name is too slow. It loops over the catalog, and `match_line` does a list lookup at each step, so 500 by 500 names is about 125 million comparisons (SC-003). Two sets, one of keys and one of all singular forms, give the same answer in linear time. A test checks that it agrees with `match_line` on a sample that includes plurals, accents and letter case (SC-004).

## R7. Failed email

- **Decision**: As with kitchen invites, the invite is saved, the email is sent, and an SMTP error rolls the transaction back. On a failed resend or repeat invite, the rollback leaves the earlier invite as it was, still open and still on the owner's list.
- **Rationale**: FR-008 is about the link that never arrived: no such link stays usable. The earlier link did arrive, and it stays visible, so the owner can cancel it. Ending it because of a passing mail outage would take a working invite away.

## R8. A new person's way in

- **Decision**: The link page's Create account button opens the plain `/signup`. The page says to open the email link again after the account is ready. The sign-up form gets no return address.
- **Rationale**: The spec's clarification says the person returns to the same link and auth stays unchanged. The sign-up form has no return path except its kitchen invite token, so returning automatically would mean changing it, which the constitution and FR-012 don't allow without approval.
- **Effect**: One extra step for a new person: after setting an alias, they land on Home and must open the email again. Signing in, setting an alias and verifying already carry `returnTo`, so those paths come back on their own.

## R9. Alias and route placement

- **Decision**: Preview and accept go on the existing `/invites` router, as `/invites/notebook/preview` and `/invites/notebook/accept`. Accept also depends on `require_user_alias`. The BFF routes sit under `/api/invites/notebook/`.
- **Rationale**: `/invites` and `/api/invites` are already public in `ui/proxy.ts`, so the proxy doesn't change. The preview must work signed out, so the router can't be gated as a whole. On `alias_required`, the link page sends the person to `aliasSetupHref(link)`.

## R10. Leaving and removal

- **Decision**: Delete the `notebook_membership` row with a plain SQL delete. No code touches locks: `fk_recipe_edit_lock_notebook_membership` cascades. Only `recipe_edit_lock` needs ending, because a recipe edit's draft is held in the browser, not on the server. The next save answers "not found". Tests cover this.
- **Rationale**: FR-026 and spec 022 FR-020b rely on this cascade. Recipe authorship is not tied to membership, so it stays (FR-027).

## R11. Locking

- **Decision**: A new `lock_notebook` takes `FOR NO KEY UPDATE` on the notebook row, in sending, resending, accepting and removing.
- **Rationale**: Sending deletes and inserts under the partial unique index, so two simultaneous sends must not collide. It's the same lock strength as `lock_kitchen`, which doesn't block the foreign-key inserts of recipe saves.

## R12. Existing behaviour checked, no change needed

- **Member access**: `facts_for`, `personal_ids_for`, `can_write_recipes` and the snapshot's owner check already treat `member` as the spec asks.
- **Capture**: `_personal` picks the only candidate without asking. A new person whose only notebook is a shared one could capture into it by that path. The Notebook tab always asks for the default notebook first, which creates it, so the case isn't reached from the tab. The browser walk checks this.
