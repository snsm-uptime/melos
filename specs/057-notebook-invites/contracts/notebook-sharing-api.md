# Contract: Notebook sharing routes

**Feature**: [../spec.md](../spec.md) | **Data model**: [../data-model.md](../data-model.md)

All routes need a session cookie, except the preview. The ui calls them through BFF routes on the same paths under `/api`, which return the api's status and body, or 502 `bad_gateway` when the api can't be reached.

## Common refusals

The routes under `/notebooks/{id}` apply these first, in this order:

| # | Check | Answer |
|---|-------|--------|
| 1 | Caller has an alias | 403 `alias_required` |
| 2 | Caller can see the notebook | 404 `notebook_not_found` |
| 3 | The notebook is personal | 403 `notebook_not_shareable` |
| 4 | Caller is the owner (where marked "owner only") | 403 `notebook_owner_only` |

## `GET /notebooks/{id}/members`

Owner and members.

```json
{
  "members": [
    { "user_id": "4c1e…", "alias": "ana", "role": "owner", "is_self": false },
    { "user_id": "9d02…", "alias": "ben", "role": "member", "is_self": true }
  ]
}
```

The owner comes first, then members by join date. `alias` is null for an account with none, and the ui shows "unknown". No email appears here.

## `DELETE /notebooks/{id}/members/me`

Leave. 204. A caller who is the owner gets 403 `notebook_owner_stays`.

## `DELETE /notebooks/{id}/members/{user_id}`

Owner only. 204. The owner as target gets 403 `notebook_owner_stays`. A person not in the notebook gets 404 `notebook_member_not_found`.

## `GET /notebooks/{id}/invites`

Owner only. Every unused invite, newest first:

```json
{
  "invites": [
    { "id": "71aa…", "email": "ben@example.test", "expires_at": "2026-11-08T15:00:00Z", "expired": false }
  ]
}
```

## `POST /notebooks/{id}/invites`

Owner only. Body: `{ "email": "ben@example.test" }`.

| Result | Answer |
|--------|--------|
| Sent | 201 `{ "status": "sent", "invite": <invite object> }` |
| Invalid email | 422 `invalid_invite_email` |
| The owner or a current member | 409 `already_in_notebook` |
| SMTP not configured | 503 `smtp_config_error`, nothing stored |
| Sending failed | 503 `smtp_send_error`, nothing stored |

The response says nothing about whether the address has an account (FR-009).

## `POST /notebooks/{id}/invites/{invite_id}/resend`

Owner only. No body. Works on open and expired invites. 200 with the same body as sending. An unknown or accepted invite gets 404 `notebook_invite_not_found`. An address now in the notebook gets 409 `already_in_notebook`. SMTP failures answer as above, and the previous link keeps working.

## `DELETE /notebooks/{id}/invites/{invite_id}`

Owner only. 204. An unknown or accepted invite gets 404 `notebook_invite_not_found`.

## `GET /invites/notebook/preview?token=…`

Public. Has no side effects.

```json
{ "notebook_name": "ana's Notebook", "inviter_alias": "ana", "email_hint": "b***n@example.test" }
```

`inviter_alias` is null when the sender no longer exists. A blank, unknown, used, expired, cancelled or replaced token gets 410 `invalid_invite_token`, always with the same body.

## `POST /invites/notebook/accept`

Body: `{ "token": "…" }`. Success is 200 `{ "notebook_id": "9a41…" }`, the same whether the caller just joined or was already in the notebook.

| Case | Answer |
|------|--------|
| No session | 401 |
| No alias | 403 `alias_required` |
| Dead link | 410 `invalid_invite_token` |
| Live link for another email | 403 `invite_email_mismatch` |
| Email not verified, when required | 403 `email_not_verified` |

Only 200 changes anything. Every other answer leaves the invite as it was. Step order is in [research.md](../research.md) R4.

## Email

Sent in the inviter's language. It names the notebook and the inviter's alias, says the link lasts 7 days, and has one link: `{PUBLIC_APP_URL}/invites/notebook?token=…`. Spanish text says "cuaderno". The name and alias are stripped of line breaks in the subject and escaped in the HTML.

## UI

| Address | Who | Behaviour |
|---------|-----|-----------|
| `/invites/notebook?token=…` signed in | Invited person | Joins on open, then goes to `/notebooks/{id}`. Handles `alias_required` through `/alias?returnTo=…` and `email_not_verified` through `/verify?returnTo=…` |
| Same, signed out | Visitor | Shows the preview, Sign in (with `returnTo`) and Create account, with a note to reopen the link afterwards |
| Share dialog, owner | Owner | Invite form, open and expired invites with resend and cancel, member list with remove |
| Share dialog, member | Member | Member list and Leave |

The share dialog opens from the share icon at the end of the chrome, as on a kitchen, on personal notebooks only; there is no separate sharing page (changed 2026-11-01 at the owner's request). Leave, remove and cancel confirm inside the same dialog. Results are announced with `role="status"` or `role="alert"`. A 404 in the dialog or on the notebook page sends the person to `/notebooks`.
