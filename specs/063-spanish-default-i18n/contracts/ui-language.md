# Contract: Language in the ui (S-063)

No api contract changes. The api surface used already exists:

| Call | Use |
|---|---|
| `GET /auth/me` (BFF `/api/auth/me`) | returns `language`: `"en"`, `"es"` or `null` |
| `PATCH /auth/me` `{ "language": "en" \| "es" }` | saves the choice; 200 returns the account; any other value is a 422 |

## Language resolution

```text
getServerLocale()                                   (server, once per request)
  signed-in account  → resolveLocale(me.language)   null / bad value → "es"
  else cookie melos_lang → resolveLocale(cookie)
  else               → "es"
```
Used by: the root layout (`<html lang>`, provider's first value) and every page that passes a `locale` prop.

## Cookie `melos_lang`

`melos_lang=en|es; Path=/; SameSite=Lax` (+ `Secure` on https). No `Max-Age`/`Expires`. Not `HttpOnly` (the browser writes it). Expired by the sign-out BFF route and cleared in the browser at sign-in and after the sign-up save. Ignored whenever an account is signed in.

## Provider

`usePreferences()` gains `setLanguage(next: Locale): Promise<void>`:

| State | Behavior | On failure |
|---|---|---|
| signed in | `PATCH /api/auth/me {language}` → update `me`, locale, `<html lang>` → `router.refresh()` | throws; locale unchanged |
| signed out | write the cookie → update locale and `<html lang>` → `router.refresh()` | cannot fail (cookie write); if cookies are blocked the choice still applies until the next load |

`useLocale()` returns the provider locale (`"en"` only when there is no provider, in tests).

## Screens

**Account** (`/account`): a "Language" radio group, options "English" and "Español", current one checked; an inline error line when the save fails ("The language could not be saved. Try again." / Spanish equivalent); the old language stays shown.

**Signed-out switch**: two small buttons "English" and "Español" at the top right of `/sign-in`, `/signup`, `/sign-up`, `/forgot-password`, `/reset-password`, `/verify`, `/invites/accept`; the current one has `aria-pressed="true"`; one tap applies at once.

**Sign-up**: after a successful register, if `melos_lang` is set, `PATCH /api/auth/me {language}` once, then clear the cookie. A failure is ignored (the account has no saved language, so Spanish).

## Messages

- `lib/i18n/*.ts` message sets are `{ en, es }` with identical keys; `capture.ts` joins them.
- `messagesFor(set, locale)` falls back to English for a missing Spanish message.
- `lib/i18n/parity.test.ts` fails the build when any set differs between languages.
- Wording: informal "tú", Latin American vocabulary, one word per concept (receta, cuaderno, cocina, ingrediente, porciones, paso).
