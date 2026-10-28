# Data Model: Language (S-063)

**No schema change and no migration.** One existing column, one new browser cookie.

## Stored (unchanged)

| Field | Where | Rule |
|---|---|---|
| `users.language` | `users` table, nullable `String(8)` | `"en"`, `"es"` or null; written only by `PATCH /auth/me` (`Literal["en","es"]`); read by `GET /auth/me`. Null and any other stored value mean "no saved language" and the interface is Spanish (FR-016). |
| `kitchen.content_language` | `kitchens` table | **not used or changed** by this feature (FR-014) |

## Browser (new)

| Name | Value | Lifetime | Written by | Read by |
|---|---|---|---|---|
| `melos_lang` cookie | `"en"` or `"es"` | browser session (no `Max-Age`); `Path=/; SameSite=Lax`; `Secure` on https | the signed-out switch | `getServerLocale()` and the provider, only when there is no signed-in account |

Removed: `localStorage["melos_lang_cache"]` and the unused server cookie of the same name.

## Derived

| Name | Rule |
|---|---|
| Interface language | signed in: `resolveLocale(me.language)`; signed out: `resolveLocale(melos_lang)`; otherwise `"es"` |
| `resolveLocale(raw)` | `raw` if it is `"en"` or `"es"`, else `DEFAULT_LOCALE = "es"` |
| Message set | `{ en, es }` with identical keys; `messagesFor(set, locale)` = English underneath, the chosen language on top |

## State transitions

```text
visitor, no cookie                → es
visitor picks English             → cookie en → en (survives reload, other tabs; gone when the browser closes)
visitor signs up with a pick      → account created → PATCH language=pick → cookie cleared → pick is the account language
visitor signs in                  → cookie cleared → account language, or es when none
member changes language           → PATCH language → state + html lang + router refresh
member signs out                  → cookie expired → es
member's language changed elsewhere → this device shows the new value on its next server render
```
