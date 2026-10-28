# Notes: Spanish by Default and Language Choice (S-063)

## Baseline (before this feature, 2026-10-28)

- ui (`npm test`): 90 files, 585 tests passed. `npm run lint` and `npm run typecheck`: clean.
- api: untouched (`git diff --stat api/` empty); this feature is ui only.
- Branch `063-spanish-default-i18n` was created from `origin/027-recipe-detail-edit-delete`, because PR #19 (servings control, chrome fix) merged into that branch and not into `main` (tasks T001 prerequisite).
- Language sources found at planning (research R0), and the command that finds each:
  `grep -rn "detectLocale\|browserLocale\|melos_lang_cache\|lang=\"en\"" ui/app ui/components ui/lib`
  - hard-coded `<html lang="en">`; provider first render "en"; local-storage `melos_lang_cache`; `browserLocale()`; `Accept-Language` on 7 pages; cookie `melos_lang_cache` read by 6 pages and never set.

## T028 audit of the message files (2026-10-28)

Found and fixed:
- **Landing page (`app/page.tsx`)** was English only. Added `lib/i18n/landing.ts` (en/es), the page reads `getServerLocale()`, and the signed-out switch shows on `/` (`showsLanguageSwitch("/")`).
- **Rate-limit text (429)** was the api's English `detail` or a hard-coded English fallback in the sign-in, sign-up, verify and forgot-password screens. Each screen now has `errorRateLimited` in both languages and never shows the api's text.
- **Sign-up refusal text** (`400 invalid_signup`) is the api's English explanation (for example the password length). It is shown only in English; in Spanish the screen's generic Spanish message is shown. Translating the api's individual reasons needs api codes per reason, which the api does not have (follow-up).
- **Screen-reader labels** "Go to Account" (avatar link), "Loading kitchen" and "Loading archived kitchens" were English; now in `account.ts` (`goToAccount`) and `kitchens.ts` (`loadingKitchen`, `loadingArchived`).
- **Account screen** read its text with `accountCopy("en")` (always English); it now follows the interface language.
- **Capture family** (`capture.ts`, the draft cards, dialogs, sheet and messages) is now English and Spanish.

Kept on purpose (no change): `components/DateRangeField` has "Previous month"/"Next month" but nothing uses it (finance leftover); the invite email placeholder `person@home.com`; the api's own `detail` strings in the BFF routes, which no screen displays; the page title and description in `app/layout.tsx` ("Melos" is the product name; the description is metadata, out of scope).

Strings identical in both languages on purpose (reviewed once, listed in `lib/i18n/parity.test.ts`): `account.en` ("English"), `account.es` ("Español"), `account.photoCropZoom` and `alias.photoCropZoom` ("Zoom"), `alias.label` ("Alias"), `capture.optionUrl` ("URL").

Plural and count functions are tested in both languages in `lib/i18n/plurals.test.ts`.

## After the build (2026-10-28)

- ui: 107 files, 745 tests passed (baseline 90 files, 585 tests). `npm run lint` and `npm run typecheck` clean.
- Guards: `lib/i18n/languageSources.test.ts` finds no `detectLocale`, `browserLocale`, `Accept-Language` read, `melos_lang_cache` or hard-coded `<html lang="en">` outside tests and the BFF routes; `grep content_language` in the language code finds nothing (FR-014); `git diff --stat api/` is empty (no api change).
- Server-built HTML against the running dev stack (`ui` hot-reloads the bind mount):
  - signed out, `Accept-Language: en-US`: `<html lang="es">` and Spanish text on `/sign-in`.
  - `Cookie: melos_lang=en`: `<html lang="en">`, English text on `/sign-in` and the landing page; the switch shows with the current language `aria-pressed`.
  - signed-in accounts (invented, removed afterwards): saved `en` + cookie `es` → `lang="en"`; no saved language + cookie `en` → `lang="es"`; saved `es` + cookie `en` → `lang="es"`. The account always wins over the cookie.
  - one page load of `/home` makes one `GET /auth/me` (and one `GET /auth/session`) to the api: the layout and the page share the cached `fetchMe`.
- Decisions: stored names such as the default notebook "ana's Notebook" are shown as stored (spec FR-008); the landing page `/` is a signed-out screen, so it was translated and carries the switch (it was not in the first spec list).
- Beyond the plan: `AccountMenu` read `accountCopy("en")` (always English) and now follows the language; the 429 rate-limit message of four signed-out screens no longer shows the api's English text.
- **Not done:** the browser walk (T034): the switch placement on `/sign-in` with the chrome header, no visible flash on reload, the capture flow end to end in both languages, longer Spanish text at phone width, and the failed-save message with the network off. The component and server-render tests cover the behaviors in jsdom and static markup only. T029's wording review: the Spanish text was drafted by the assistant and should be reviewed by the owner before release (spec assumption).
- Timing (SC-003, SC-008): a language change is a state update plus `router.refresh()`; not measured in a browser.
