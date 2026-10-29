# Contract: Recipe edit lock (amends spec 027 `contracts/recipe-api.md`)

## POST /recipes/{recipe_id}/edit-lock

Take the lock for the caller's session, or for the holder: keep-alive (research R10). 200 `{"editor": {"alias": "...", "is_me": true, "idle_expires_at": "ISO-8601"}}`.
- 404 `recipe_not_found` (cannot read), 403 `read_only` (cannot write, incl. archived kitchen),
- 409 `recipe_locked` with `editor_alias` when another live session holds it.

## DELETE /recipes/{recipe_id}/edit-lock

Release if the caller's session holds it. 204, idempotent.

## Changes to spec 027 routes

- **GET /recipes/{id}**: adds `editor: {alias, is_me} | null`. `can_write` stays the permission; the ui disables Edit and Delete when `editor` is set and `is_me` is false.
- **PUT /recipes/{id}**: requires the caller's session to hold a live lock, else 409 `recipe_locked` (another holder) or 409 `not_editing` (nobody). On success the lock is released. The `version` check (409 `stale`) stays.
- **DELETE /recipes/{id}**: 409 `recipe_locked` while another live session holds the lock. A delete by the holder succeeds; the lock cascades.
- **GET /recipes/{id}** also adds `in_cart: bool` and `cart_editor: {alias, is_me} | null` for kitchen-notebook recipes (null fields for personal notebooks), so the detail page can show Add/Remove and the cart notice.

## Idle limit and access loss

- A recipe lock ends 5 minutes after the holder's last activity (acquire or keep-alive). The edit page sends a keep-alive at most every 30 s while the member types, and shows a warning 1 minute before `idle_expires_at` with **Keep editing** (keep-alive). After expiry, `PUT` answers 409 `not_editing`; the page keeps the typed edits on screen and offers to start a new edit.
- Losing write access deletes the lock (research R11); getting access back does not restore it.
