# Implementation Plan: Spanish by Default, with English and Spanish for Every Screen

**Branch**: `063-spanish-default-i18n` (spec folder `063-spanish-default-i18n`, story S-063) | **Date**: 2026-10-28 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/063-spanish-default-i18n/spec.md`

## Summary

Spanish becomes the interface language for everyone without a saved language, English or Spanish can be chosen (in the account, or on a small switch on the signed-out screens), and every screen, including the capture flow and the cards it shares with the recipe pages, shows text in that language.

Technical approach: **ui only. The api is not changed.** `users.language` and `PATCH /auth/me {language}` already exist, so the account is the source of truth for a signed-in member. The work is making every part of the ui agree on one source:

- A server function `getServerLocale()` decides the language for every server-built page and for `<html lang>`: the signed-in account's saved language (read with the existing `fetchMe`, now returning `language`), else the signed-out pick cookie, else Spanish. The root layout passes it to `PreferencesProvider` as its first value, so server and browser start identical and nothing flips.
- The five other places that guess a language today are removed: `Accept-Language` detection on seven signed-out pages, the browser's own language, a `melos_lang_cache` value in local storage, a cookie of the same name that nothing ever sets (so server pages always render English), and the hard-coded `lang="en"`.
- The signed-out pick is a small session cookie (`melos_lang`) that the server can read, set by a switch the app shell shows on the signed-out screens; sign-up saves it to the new account with the existing `PATCH`, and sign-in and sign-out clear it.
- The capture message set becomes `{ en, es }` and is read through a `useCaptureMessages()` hook, so the draft editor, the text sheet, the dialogs, the error messages and the shared ingredient, step, and row cards follow the interface language. A parity test fails the build when a message exists in one language only.

## Technical Context

**Language/Version**: TypeScript, Next.js 16 App Router, React 19, Tailwind 4 (`ui/`). No Python change.

**Primary Dependencies**: Existing only: `next/headers` `cookies()`, React `cache`, `PreferencesProvider`, `fetchMe`, the `lib/i18n/*` message files. **No new library.**

**Storage**: PostgreSQL `users.language` (nullable, already exists, written by `PATCH /auth/me`). One session cookie `melos_lang` in the browser for the signed-out pick. No migration. No other storage; the old local-storage language cache is deleted.

**Testing**: vitest + eslint + typecheck. Pure tests (locale resolution, cookie helper, parity of all message sets), server tests with mocked `cookies()` and `fetchMe` (`getServerLocale`, layout, pages), component tests in both languages (switch, account choice, capture family, shared cards, detail and edit), provider tests (initial value, both `setLanguage` paths, failure). An HTTP check against the running dev stack that server-built HTML carries the right text and `lang` for each source. A browser walk in both languages at phone width (constitution §6).

**Target Platform**: Mobile-first browser ui under Docker Compose.

**Project Type**: Web application; this change is in `ui/` only.

**Performance Goals**: A language change shows within 1 s without reload (SC-003, SC-008): a state change plus a router refresh. The extra per-request cost is one `fetchMe` shared with the pages' own `requireAlias` through `cache`, and none for visitors without a session cookie.

**Constraints**:
- The authentication layer is untouched: language is saved with the existing `PATCH /auth/me` (constitution §1).
- A remembered value must never outrank the account's saved language (FR-010).
- No cookie or storage keeps a signed-out pick beyond the browser session (FR-013).
- Stored text (recipes, names, aliases) is never translated (FR-008); `kitchen.content_language` is not read or written (FR-014).
- The ui text lives in message files only, one place per message (constitution: strings once, spec 017).

**Scale/Scope**: About 14 message files audited, one (`capture.ts`) restructured and about 14 components moved to the hook, 7 server pages and the layout moved to one function, 1 provider reworked, 3 new small components (account choice, signed-out switch, language helpers).

## Constitution Check

*GATE: passed before Phase 0 and re-checked after Phase 1 design.*

| Principle | Result |
|---|---|
| 1. Simplicity and reuse | Pass. No new service, route, library or table. Uses `PATCH /auth/me` and `fetchMe` as they are. Auth layer unchanged: sign-up saves the pick with a second call, not a changed endpoint. |
| 2. Tech stack | Pass. No dependency added. |
| 3. Hexagonal | Pass. Nothing in `api/` changes. |
| 4. Security and privacy | Pass. The only new browser value is `en` or `es` in a session cookie; no personal data. The cookie is read, never trusted for access. |
| 5. No AI shortcuts | Pass. No model involved; recipe content is not translated. |
| 6. Testing | Pass. Pure, server, component, provider and parity tests plus an HTTP check and a browser walk. |
| 7. Deployment | Pass. No compose or server change. |
| 8. Git discipline | Pass. No schema change; small commits per layer. |
| 9. Scope | Pass for a *Should* item added by the owner on 2026-10-28. |

Post-design re-check: unchanged. No violations, so Complexity Tracking is empty.

## Project Structure

### Documentation (this feature)

```text
specs/063-spanish-default-i18n/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/ui-language.md
├── checklists/requirements.md
└── tasks.md              # /speckit-tasks, not created here
```

### Source Code (repository root)

```text
ui/
├── app/
│   ├── layout.tsx                         # <html lang>, initial locale from getServerLocale()
│   ├── api/auth/sign-out/route.ts         # also expires melos_lang
│   ├── {home,kitchens/[kitchenId],notebooks,notebooks/[notebookId],recipes/[recipeId],recipes/[recipeId]/edit}/page.tsx
│   │                                      # resolvePageLocale(cookie) → getServerLocale()
│   └── {sign-in,signup,forgot-password,reset-password,verify,alias,invites/accept}/page.tsx
│                                          # detectLocale(accept-language) → getServerLocale()
├── components/
│   ├── PreferencesProvider.tsx            # initialLocale, setLanguage, no local-storage language
│   ├── AppShell.tsx                       # mounts the signed-out switch on signed-out paths
│   ├── AccountMenu.tsx                    # + language choice
│   ├── LanguageChoice.tsx                 # NEW: English | Español radio group (account)
│   ├── SignedOutLanguageSwitch.tsx        # NEW: small switch for signed-out screens
│   ├── RecipeDraft/*, AddRecipeCallToAction/*, RecipeEdit/*, RecipeDetail/*
│   │                                      # useCaptureMessages(); explicit locale where already passed
├── lib/
│   ├── serverLocale.ts                    # NEW: getServerLocale()
│   ├── alias.ts                           # fetchMe() cached, returns language; skips fetch with no session cookie
│   ├── appChrome.ts                       # + showsLanguageSwitch(pathname)
│   └── i18n/
│       ├── locale.ts                      # DEFAULT_LOCALE = "es", LANGUAGE_COOKIE, resolveLocale; detectLocale/browserLocale removed
│       ├── languagePick.ts                # NEW: read/write/clear the melos_lang cookie
│       ├── messages.ts                    # NEW: messagesFor(set, locale) with fallback to English
│       ├── capture.ts                     # { en, es } + captureMessagesFor(locale) + messageForCode(msg, locale)
│       └── parity.test.ts                 # NEW: every message set has the same keys in en and es
```

**Structure Decision**: ui only, in the existing places. One server function and one cookie helper replace six ad hoc sources. The capture family moves to a hook rather than a prop on every component, because those components are shared by three screens (draft, edit, detail) that already pass `locale` in different ways.

## Complexity Tracking

No violations to justify.
