# Research: Spanish by Default and Language Choice (S-063)

No `NEEDS CLARIFICATION` remained. This is the audit of today's behavior and the decisions the plan rests on.

## R0. What decides the language today (the problem)

| # | Source | Where | Effect |
|---|---|---|---|
| 1 | `<html lang="en">` hard-coded | `app/layout.tsx` | the page declares English whatever it shows |
| 2 | `PreferencesProvider` first render is `"en"` | `components/PreferencesProvider.tsx` | every client screen flashes English, then flips |
| 3 | `localStorage["melos_lang_cache"]` | provider + boot script | a remembered value applied before the account answers |
| 4 | `navigator.language` (`browserLocale`) | provider fallbacks | an English browser gets English even with no choice |
| 5 | `Accept-Language` header (`detectLocale`) | 7 signed-out server pages | server pages follow the browser header |
| 6 | cookie `melos_lang_cache` | 6 signed-in server pages (`home`, `kitchens/[id]`, `notebooks`, `notebooks/[id]`, `recipes/[id]`, `recipes/[id]/edit`) | **nothing ever sets this cookie** (the provider writes local storage, not a cookie), so these pages always render English |
| 7 | `users.language` via `GET /auth/me` | provider after mount | the real source, applied late |

Also: `capture.ts` and the components that use it are English only, and the language selector was removed from the account (S-005).

## R1. One source for the server

- **Decision**: `getServerLocale()` in `ui/lib/serverLocale.ts`, wrapped in React `cache` so it runs once per request: if there is a signed-in account, `resolveLocale(me.language)`; otherwise `resolveLocale(cookie melos_lang)`; otherwise `DEFAULT_LOCALE` (`"es"`). `resolveLocale` returns the value only for `"en"` or `"es"` and `"es"` for anything else, including `null` and a bad stored value (FR-016). `fetchMe()` gains `language`, is itself wrapped in `cache`, and returns `null` at once when there is no session cookie, so signed-out visitors cost no api call and the pages' own `requireAlias` shares the same call.
- **Rationale**: Every server page and the layout call one function, so they cannot disagree. The account wins over the cookie (FR-018). No api change.
- **Alternatives**: a language cookie for signed-in members too (a second copy that goes stale when the language is changed on another device, rejected by FR-010 and US4 scenario 4); passing the language in the address (leaks into links); reading the language only in the browser (the status quo flash).

## R2. The first value in the browser

- **Decision**: The root layout is a server component: `const locale = await getServerLocale()`, `<html lang={locale}>`, `<PreferencesProvider initialLocale={locale}>`. The provider's initial state is that value, with no `"en"` start, no local-storage read and no `browserLocale()`. The boot script keeps only the theme part.
- **Rationale**: Server HTML and the first client render match, so there is no flip (FR-011, SC-005) and no hydration warning.
- **Alternatives**: keep `suppressHydrationWarning` and fix it up after mount (still flashes).

## R3. The signed-out pick (spec Option B)

- **Decision**: A session cookie `melos_lang=en|es` (`Path=/; SameSite=Lax`, no `Max-Age`, `Secure` on https), written by the browser from the switch, read by `getServerLocale()` only when there is no signed-in account. It is cleared in the browser on successful sign-in and by the sign-out BFF route (which already expires `melos_session`).
- **Rationale**: The server must see the pick on the first request or the page flashes Spanish for an English picker; a cookie is the only thing the server sees. A session cookie ends when the browser closes, which is the "not remembered for later visits" the owner chose. The spec's wording was changed from "the open tab" to "the browser session" to match; a tab-only value (`sessionStorage`) cannot be read by the server and would flash on every signed-out page load.
- **Alternatives**: `sessionStorage` (flash, exact tab semantics); a persistent cookie (Option C, rejected by the owner).

## R4. Changing the language

- **Decision**: `PreferencesProvider.setLanguage(next)`:
  - signed in (`me` is set): `PATCH /api/auth/me {language}`; on success update `me`, the locale and `document.documentElement.lang`, then `router.refresh()`; on failure throw, leaving the locale as it was (FR-005).
  - signed out: write the `melos_lang` cookie, update the locale and `lang`, then `router.refresh()`.
- **Rationale**: State gives the instant change on client components; `router.refresh()` re-renders server pages so their `locale` props change without a reload (FR-004, SC-003). The server rereads the account, so a stale device converges on its next load (US4 scenario 4).
- **Alternatives**: make every screen read the provider (a larger change across ~25 files, no extra benefit once refresh works).

## R5. Sign-up, sign-in, sign-out

- **Decision**: After a successful sign-up the signup client reads the `melos_lang` pick and, if present, sends `PATCH /api/auth/me {language}` once, then clears the cookie; if the call fails the account simply has no saved language (Spanish). A successful sign-in clears the cookie in the browser. The sign-out route expires `melos_lang` with `melos_session`.
- **Rationale**: Honors FR-018 without touching the auth layer (constitution §1): `PATCH /auth/me` already accepts a language and needs only a session, which register creates.
- **Alternatives**: add `language` to `POST /auth/register` (an auth-layer change that needs approval).

## R6. The signed-out switch

- **Decision**: `SignedOutLanguageSwitch` (two small buttons, "English" / "Español", the current one marked with `aria-pressed`), mounted by `AppShell` on the signed-out paths from `showsLanguageSwitch(pathname)`: `/sign-in`, `/signup`, `/sign-up`, `/forgot-password`, `/reset-password`, `/verify`, `/invites/accept`. It is placed at the top right of the screen. Each label is written in its own language, so it reads the same in both.
- **Rationale**: One place instead of seven pages; `appChrome.ts` already owns path lists.
- **Alternatives**: a switch inside each form (seven copies).

## R7. The account choice

- **Decision**: `LanguageChoice` (a `radiogroup` with "English" and "Español") inside `AccountMenu`, between theme and password reset, calling `setLanguage`; it shows an error line when the save fails. The current language is marked even when it is the default (it shows Spanish as selected, US2 scenario 6 only distinguishes after the member chooses; the saved value `me.language` is available to tell "chosen" from "default" for tests).
- **Rationale**: The spec asks for a choice with the current one marked; reuse the theme control's location and pattern.

## R8. Moving the capture family to both languages

- **Decision**: `captureMessages` becomes `{ en, es }` with `type CaptureMessages = typeof en`, so a missing Spanish key is a type error. `captureMessagesFor(locale)` returns `messagesFor(captureText, locale)`; `useCaptureMessages()` is `captureMessagesFor(useLocale())`; `messageForCode(message, locale)` and the draft-rule error text take the locale. Components that already receive `locale` (detail, edit) pass it down; shared rows (`IngredientLineRow`, `StepCard`, `RowControls`, `NameChangeNotice`) take an optional `locale` prop and fall back to `useLocale()`.
- **Rationale**: The shared cards must follow the screen around them (FR-007). Typing makes parity a compile-time guarantee for this file and the parity test covers the rest.
- **Alternatives**: a global i18n library (a new dependency, rejected by the stack rule); passing `locale` through every component (heavy).

## R9. `useLocale()` outside the provider

- **Decision**: `useLocale()` returns the provider's locale, and `"en"` only when there is no provider, which happens in component tests. Production always has the provider (root layout). Existing tests that assert English strings keep passing; new tests wrap or mock the provider to check Spanish.
- **Rationale**: Keeps ~25 existing test files unchanged. The fallback is documented in the hook.
- **Alternatives**: default to Spanish and edit every test (large churn for no product value).

## R10. Fallback and parity (FR-009)

- **Decision**: `messagesFor(set, locale)` returns `{ ...set.en, ...set[locale] }`, so a missing Spanish message shows English, never blank. `lib/i18n/parity.test.ts` imports every message set and asserts the same key paths exist in both languages and that function messages have the same arity; it fails the build on any difference (SC-002).
- **Rationale**: Runtime safety and a build-time guarantee.

## R11. Audit of the files that already have both languages

- **Decision**: Review `account`, `alias`, `invite`, `kitchens`, `notebooks`, `password-reset`, `recipeDetail`, `recipeLists`, `signin`, `signup`, `verify` for missing or English-only strings (for example the labels of the shared cards), add what is missing, and keep the rest. Spanish uses informal "tú" and Latin American vocabulary, as the existing text does.
- **Rationale**: The spec requires every listed screen; the audit finds the gaps rather than assuming.

## R12. What stays out

- Emails, number format (decimal point), stored names such as "ana's Notebook", `kitchen.content_language`, page `<title>` ("Melos" is the product name), and the `description` metadata.
- **Rationale**: Each is named in the spec's out-of-scope list or assumptions.
