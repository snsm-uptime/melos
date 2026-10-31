# Research: Kitchen Side Panel

No NEEDS CLARIFICATION remained. These are the design decisions.

## R1. Where the default kitchen lives

- **Decision**: Nullable `users.default_kitchen_id` (FK `kitchens.id`, `ON DELETE SET NULL`), read and set through a new `/side-panel` route.
- **Rationale**: It mirrors `users.default_notebook_id`. The auth layer changes need approval and the spec says it is not changed, so `MeResponse` and `PATCH /auth/me` stay as they are.
- **Alternatives considered**: A new field on `PATCH /auth/me`, rejected because it edits auth routes. A flag on `kitchen_membership`, rejected because "exactly one" would need an extra constraint.

## R2. Sign-up kitchen, existing people and fallback

- **Decision**: Resolve on read, then store the result if it changed. Keep the stored kitchen when the person belongs to it and it is active. Otherwise take their earliest-created active kitchen they own, then their earliest-joined active kitchen, then none.
- **Rationale**: Every account owns its sign-up kitchen, so "earliest owned" finds it, for invitees too, with no signup change and no data backfill. The same rule covers archive, delete and leave. Storing the result makes the fallback the new default, as the spec's assumption says, so restoring the old kitchen does not switch back.
- **Alternatives considered**: Backfill in the migration plus a write at signup, rejected because it needs an auth change and still needs the fallback.
- **Note**: The spec says "first remaining active kitchen". Owned kitchens come first here, so Home stays on the person's own kitchen.

## R3. Recipe count

- **Decision**: `COUNT` of recipes with `author_id` = the caller, in a notebook of a kitchen they belong to (archived included) or a personal notebook they own or are a member of.
- **Rationale**: FR-005. An archived kitchen is still reachable through the archive toggle.
- **Alternatives considered**: A stored counter, rejected because it can drift and a read is cheap.

## R4. Keeping the panel current

- **Decision**: The kitchen list uses the existing membership store. `unarchiveKitchen` is changed to update it. The panel refetches kitchens and `/side-panel` on every path change and after a kitchen action.
- **Rationale**: FR-017 and SC-006 with no polling. Refetching on navigation also shows the removal from a kitchen when the person next moves.
- **Alternatives considered**: Polling or push, rejected as beyond the spec.

## R5. Open or closed state

- **Decision**: `localStorage` key `melos_side_panel_open`, read through `useSyncExternalStore` with closed as the server value. Larger screens only; layout switches with CSS at `md`.
- **Rationale**: Per device (spec assumption). CSS avoids a wrong layout on first paint. A person who left it open sees one brief closed frame, which is accepted.
- **Alternatives considered**: A cookie for server rendering, rejected as more machinery for one frame.

## R6. Phone drawer

- **Decision**: On phones a menu button is the first item in the header, and the header always shows on app pages. It sits beside Back on nested pages. The drawer has a backdrop, closes on Escape, on a backdrop tap and after choosing an entry, and starts closed on each load.
- **Rationale**: FR-018 says the panel covers content, so leaving it open after navigation would hide the page. US2 scenario 4 and SC-005 therefore apply to larger screens.

## R7. `/home` and old URLs

- **Decision**: `/home` redirects to the default kitchen. With no kitchens it shows the create prompt. `/kitchens` keeps redirecting to `/home`. Kitchen pages lose their Back to `/home`, since the panel replaces it.
- **Rationale**: Existing links, sign-in landing and Back paths keep working. Landing still prefers the last opened kitchen (S-012).

## R8. Kitchen header row

- **Decision**: From `md` up, the icon buttons sit in the row as FR-016 says. On phones, rename, archive or restore, delete and set default go behind the existing dots menu button, while cart and invite stay visible.
- **Rationale**: Six 44px buttons leave almost no room for the title on a 360px phone. This is a small reading of FR-016, chosen for phones only.

## R9. Set default control

- **Decision**: A home icon button in the kitchen header for every member, on active kitchens that are not already the default.
- **Rationale**: The spec requires the action (FR-006a) but names no place, and it belongs with the other kitchen actions.

## R10. Kitchen icons when closed

- **Decision**: A rounded square with the kitchen's first letter, coloured by `lib/avatarColor.ts` from the kitchen id, plus a tooltip and accessible name.
- **Rationale**: FR-012. The colour separates kitchens with the same initial.

## R11. Log out

- **Decision**: Move `onSignOut` from `AccountMenu` to `lib/signOut.ts`, unchanged. `onPasswordReset` stays and uses the same steps with its own target page.
- **Rationale**: FR-014 asks for the same behaviour, and the two handlers are already identical but for the target.

## R12. Toasts

- **Decision**: Toasts sit at the bottom of the content area with the safe-area padding, as there is no tab bar.
