# Quickstart: validate S-063 end to end

Prerequisites: the stack runs through Compose (`./scripts/compose-up.sh`); two accounts with aliases: one with no saved language (any existing seed account) and one with English saved (`PATCH /api/auth/me {"language":"en"}`). Use invented data only.

## 1. Automated checks

```sh
cd ui && npm test && npm run lint && npm run typecheck
```
Expected: the new parity, locale, cookie, server-locale, provider, switch, account-choice, capture-family and Spanish screen tests pass; earlier tests are unchanged. No api or Compose test run is needed: nothing in `api/` changes.

## 2. Server-built HTML (no browser needed)

```sh
# signed out, English browser header: still Spanish
curl -s -H 'Accept-Language: en-US,en' localhost:3000/sign-in | grep -o '<html[^>]*lang="[a-z]*"'      # lang="es"
curl -s localhost:3000/sign-in | grep -o 'Iniciar sesión' | head -1                                       # Spanish text
# signed-out English pick in the cookie
curl -s -H 'Cookie: melos_lang=en' localhost:3000/sign-in | grep -o '<html[^>]*lang="[a-z]*"'            # lang="en"
curl -s -H 'Cookie: melos_lang=en' localhost:3000/sign-in | grep -o 'Sign in' | head -1                   # English text
# signed in with English saved: the cookie is ignored, the account wins
curl -s -b 'melos_session=<token of the English account>; melos_lang=es' localhost:3000/home | grep -o '<html[^>]*lang="[a-z]*"'   # lang="en"
```

## 3. Browser walk (constitution §6), in both languages, at phone and desktop width

1. Clear cookies. Open `/sign-in` in a browser set to English. **Expect** Spanish, a switch with "Español" pressed, no moment in English.
2. Press "English". **Expect** English at once; reload: still English, no flash; open `/signup` in a new tab: English; close the browser and reopen: Spanish.
3. Sign up with English picked. **Expect** every screen after sign-up in English; account shows English chosen. Sign out: sign-in is Spanish.
4. Sign in to an account with no saved language. **Expect** Spanish; in the account screen the language choice shows Español; choose English: the screen turns English at once, home and a notebook are English, reload keeps English.
5. Sign in to the same account from a second browser. **Expect** English. Change to Spanish there; in the first browser reload a page: Spanish.
6. In Spanish walk: home, a kitchen, a notebook and its recipe list, **add a recipe from text** (options, text sheet, draft editor, ingredient and step cards, name-change notice and undo, an error such as "not a recipe", save), the recipe detail (servings control, ingredient and step cards), edit, delete dialog, account. **Expect** no English interface text. Repeat in English: no Spanish.
7. Phone width: check longer Spanish text keeps every button visible and nothing scrolls sideways.
8. A recipe titled in English, viewed in Spanish. **Expect** the title, ingredient names and notes unchanged.
9. With the network off, choose a language in the account. **Expect** an error line and the previous language still shown.

## 4. Data check

After step 4, `users.language` of that account is `en` (psql); `kitchens.content_language` of its kitchens is unchanged.
