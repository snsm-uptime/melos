# Quickstart: validate notebook sharing

**Feature**: [spec.md](spec.md) | **Routes**: [contracts/notebook-sharing-api.md](contracts/notebook-sharing-api.md)

## Prerequisites

- Migration `0012_notebook_invite` applied. Check upgrade, downgrade and upgrade again on a scratch database.
- Invented accounts only: `ana@example.test` with a notebook and recipes, and `ben@example.test` with his own recipes.
- SMTP settings that let you read the sent email in development.
- For the browser walk on this WSL host, use an isolated stack and do not start a second Compose project with the main `.env`.

## Automated checks

```bash
docker compose -f docker-compose.yml -f docker-compose.test.yml run --rm --build api
cd api && uv run ruff check .
cd ui && npm test && npm run lint && npm run typecheck
```

All must pass. The suites must include:

| Area | Proves |
|------|--------|
| `names_to_add` | Agrees with `match_line`; plurals, accents and letter case (SC-004); 500 by 500 names under 2 seconds (SC-003) |
| Access | Non-owners refused on invite, cancel, resend and remove; "not found" after leaving or removal (SC-005) |
| Dead links | Used, expired, cancelled and replaced links give identical answers (SC-006) |
| Forced failures | A failure at each accept step leaves 0 memberships and 0 names, and the invite usable (SC-007) |
| Simultaneous accepts | One membership, one merge (FR-015) |
| Locks | Removal ends the person's `recipe_edit_lock` rows (FR-026) |

## Browser walk

Do each at 360px and 1280px, in English and Spanish, and once with a keyboard only.

1. **Invite and join (US1)**: As Ana, open the notebook, press the share icon at the end of the chrome, then send to Ben. As Ben, signed in, open the email link. Expected: he lands on the notebook with no Join step.
2. **Signed out**: Open a link signed out. Expected: notebook name, Ana's alias and a masked email. Sign in returns to the link and joins.
3. **Wrong person**: Open a link as a third account. Expected: the mismatch message, and the link still works for Ben.
4. **Shared work**: Ben edits a recipe, and Ana sees the change (AC1a.1). Ben captures into the notebook. His list shows it as member with Ana's alias. He has no invite, rename or delete controls.
5. **Merge (US2)**: Ana has "onion" and Ben has "onions" and "saffron". After he joins, the catalog has "onion" and "saffron", and no "onions" (AC1a.3).
6. **Leave and remove (US3)**: Ben opens a recipe for editing, and Ana removes him. Expected: his next save answers "not found", the app takes him to his notebooks, and Ana can edit the recipe. His recipes stay, with his alias. Invite him again and he rejoins. Then have him leave.
7. **New person (US4)**: Invite an unused address. Create an account with it, set an alias, open the link again. Expected: joined. Repeat with another address and a different account: mismatch. With verification on: asked to verify, then joined.
8. **Sharing view (US5)**: Send two invites. Cancel one and resend the other. Expected: the cancelled link and the first resent link show the invalid message, and the newest link works. As a member, no invites are shown.
9. **Refusals**: A kitchen notebook has no share icon. Inviting yourself or a member gives the plain message. With SMTP broken, the owner sees an error and no new invite appears.
10. **Capture after joining**: As a new person whose only notebook is a shared one, open the Notebook tab, then capture from a notebook page. Expected: their own default notebook is listed too (R12). The tab's plus tile makes a notebook now, not a recipe.
