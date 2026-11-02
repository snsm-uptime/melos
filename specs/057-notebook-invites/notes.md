# Notes: Share a notebook by email invite

## How the checks ran

The tasks name `docker compose ... docker-compose.test.yml run --rm --build api`. That overlay uses the dev `db` service, so the api suite ran the way CI does instead: `uv run pytest` against a throwaway tmpfs `pgvector/pgvector:pg16` container on its own port, with the CI environment. The Compose command itself was not run.

## Baseline (T002), `main` at 12bde88

- api: 1029 passed, ruff clean.
- ui: 1121 passed.
- No failures predate this story.

## Migration (T011)

On a scratch database with an invented user, notebook and invite: upgrade to `0012_notebook_invite`, a second open row for the same notebook and email refused by `uq_notebook_invite_open`, downgrade (table gone, user and notebook kept), upgrade again (revision `0012_notebook_invite`).

## Decisions made while building

- **Access before email check**: T016 validates the email first, the contract applies its refusals first. Built as the contract says, so a member or stranger with a bad address gets the access refusal.
- **410 text**: `InvalidInviteTokenError.MESSAGE` speaks of a kitchen, so notebook routes send `INVALID_NOTEBOOK_INVITE_MESSAGE` under the same code.
- **Route pin updated**: `test_notebook_routes_are_gets_on_the_four_contract_paths` now lists the six sharing paths with their methods.
- **Notebook page on 404**: it now goes to `/notebooks`, including when a list reload answers 404; the old test of the message was replaced.
- **BFF**: the new routes reuse `forwardRecipeRequest`, which already handles the cookie, 204 and 502.
- **SMTP response**: moved from `routes/kitchens.py` to `api/smtp_responses.py`, unchanged.

## Automated checks (T054)

api: 1158 passed against a throwaway Postgres, ruff check and format clean. ui: 1174 passed, lint and typecheck clean. Run with the CI setup described above, not the Compose command.

## Browser walk (T055)

125 of 125 checks passed on an isolated stack (host api, a copy of the ui, tmpfs Postgres, local SMTP sink), at 360px and 1280px in English and Spanish, plus one keyboard-only pass in English at 1280px. It covers quickstart steps 1 to 6 and 8 to 10, and step 7 without verification.

- **Step 7 with email verification on**: 3 of 3 checks passed in a separate run, with the api started with verification required: the person is asked to verify with a return link, the invite stays open, and once verified the same link joins them. The account was marked verified directly in the database, not through the emailed verification link.
- **Step 6**: after removal, a save on an open edit page shows "no longer available" with a link to the notebooks. It does not redirect by itself. Opening the notebook does redirect.
- **Step 10 (R12)**: a new person whose first notebook is a shared one also has their own default, seen in `/notebooks` after opening the Notebook tab. Capture itself was not driven in the browser.

## Changes after the walk (owner's request, 2026-11-01)

- **Sharing moved to the chrome**: a share icon at the end of the chrome opens a dialog, like the kitchen's. It replaces the text link and the `/notebooks/{id}/sharing` page. Members get the icon too, because the dialog holds the people list and Leave; a kitchen shows it to the owner only.
- **New notebook**: the plus tile on the Notebook tab now asks for a name, creates a personal notebook and opens it, empty. It replaces the add-recipe tile there, so recipes are added from a notebook's page. `POST /notebooks` is the creation part of S-059; rename and delete are not built.
- **Checks**: api 1168 passed, ui 1182 passed, lint and typecheck clean. A browser run of these flows passed 45 of 45 checks at 360px and 1280px in both languages. The earlier 128-check walk ran before this change and was not repeated; this run repeats inviting, joining, removing and leaving through the dialog, not cancel or resend.
