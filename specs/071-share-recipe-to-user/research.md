# Research: Share a recipe with a person from the recipe page

Each unknown from the plan's Technical Context, with the decision taken.

## R-1 Ordering: "most recent shared activity"

- **Decision**: Order co-members by the most recent membership grant time across the kitchens and
  notebooks the two people share (the later of the two join times, taking the maximum over shared
  contexts), then by alias, case-insensitive. If no join timestamp is stored on the membership
  rows, fall back to alias order only, as the spec allows.
- **Rationale**: The spec asks for recent cooking partners first and allows alphabetical as the
  fallback. Membership timestamps are the closest durable signal already in the data.
- **Alternatives considered**: a new "last cooked together" activity log (new table and writes on
  every edit: rejected as scope creep for a post-MVP story); recipe authorship recency (not the
  same as sharing a kitchen).
- **Open item**: confirm in `api/adapters/persistence/migrations/` whether `kitchen_memberships` and
  `notebook_members` carry a created/joined timestamp. If they do not, the fallback applies and the
  owner is told the order is alphabetical in this version.

**Resolved (T001, 2026-11-05).** `kitchen_memberships` and `notebook_membership` both have a
`created_at` join timestamp (`api/adapters/persistence/models.py`). The ordering is therefore by
recent shared activity, then alias; no alias-only fallback is needed.

## R-2 Schema and co-member lookup

- **Decision**: No migration. Co-members are derived with one SQL query in a new adapter file
  `adapters/persistence/co_members.py`: users with a `kitchen_memberships` row in a kitchen the
  caller also belongs to, union users with a `notebook_members` (or owner) row on a notebook the
  caller also belongs to, minus the caller, distinct by user id. Archived kitchens are included only
  if the spec says so; default assumption: included, since membership still gives access to read.
- **Rationale**: Reuses existing membership tables. Matches the spec's "share a kitchen or a
  notebook" definition exactly.
- **Alternatives considered**: a materialised "contacts" table (needs maintenance on every join and
  leave: rejected).
- **Note for implementation**: archived-kitchen membership must be decided before coding; flagged as
  an assumption to confirm with the owner, not blocking.

**Resolved (T004 default).** Archived kitchens are included: the owner was not asked
interactively, so the default in this note applies. Owner to confirm.

## R-3 Name normalization (the S-048 step)

- **Decision**: Build the single-recipe copy step here, and make it normalize ingredient names
  against the target notebook's catalog with the S-018 matcher, target names winning, as PRD 1.5G
  says. The existing kitchen copy (spec 069) only calls `catalog.add_names` without matching; that
  path is not changed by this feature. The new service is written so S-048 can reuse it later.
- **Rationale**: The spec's edge case requires normalization; S-048 is backlog and this story
  depends on the copy, so building the shared part here avoids a blocked story.
- **Alternatives considered**: copy with no normalization (violates the edge case and the PRD);
  wait for S-048 (blocks the owner's next story).
- **Risk**: The S-018 matcher's interface must be read before tasks are written; if it is not
  callable from `application/`, the matcher call goes behind an existing port.

**Resolved (T003).** The S-018 matcher is `propose_entry(name, catalog)` in
`api/domain/ingredient_catalog.py`, built on `match_line` and `singular_forms`. It is pure, so
`application/recipe_share.py` calls it directly. The renames are written by the new
`RecipeRepository.rename_line_names` port method.

## R-4 Double send

- **Decision**: Client-side single-flight: the send button is disabled as soon as a send starts and
  stays disabled until the response. Server side, the send is one transaction (as the kitchen copy
  is), so a failed request copies nothing.
- **Rationale**: Prevents two requests from one press. The server does not dedupe identical
  requests in this version.
- **Alternatives considered**: an idempotency key per press (small extra table or header store:
  deferred unless a duplicate copy is seen in testing). Recorded as a known gap in quickstart.

## R-5 Recipient default notebook

- **Decision**: Use `users.default_notebook_id` (AGENTS.md: "Every person gets a default one… on
  first use"). If it is null, the default is created on first use by the existing helper, not by
  this feature. If no default can be resolved, the send is refused with a message and no copy is
  made (spec edge case).
- **Rationale**: Matches the domain rule already in AGENTS.md and avoids a second default-notebook
  path.

**Resolved (T002).** `users.default_notebook_id` exists. The helper is
`ensure_default_notebook` in `api/application/notebooks.py`; it creates the default on first use
under the user-row lock, so the share calls it for the recipient.

## Summary of decisions

| # | Decision | Impact |
|---|----------|--------|
| R-1 | Order by membership join time, then alias; alias-only fallback | Confirm timestamp columns |
| R-2 | No migration; one co-member SQL query | Port method + adapter file |
| R-3 | Build the shared copy with name matching here | Read S-018 matcher first |
| R-4 | Client single-flight; one transaction server-side | Known gap: no server dedupe |
| R-5 | Use `default_notebook_id`; refuse if unresolvable | Error code in contract |
