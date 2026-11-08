# Contract: the disclaimers preference

A yes/no personal preference of the signed-in member, on by default, kept on the account (FR-013c). This feature is its first use; it is worded generally ("Show disclaimers") so later disclaimers follow it.

## Api

`GET /auth/me` response gains:

```json
{ "disclaimers": true }
```

`PATCH /auth/me` body gains an optional field:

```json
{ "disclaimers": false }
```

- `disclaimers`: `bool | null`. `null` or absent means "not sent": other fields work as today and the stored value is unchanged. Any non-boolean value is refused by body validation (422), like a bad `theme`.
- The response of `PATCH /auth/me` is the `GET /auth/me` body, so the client reads the saved value back.
- `GET /auth/me` always returns a boolean (the column is `NOT NULL`), `true` for accounts that never changed it.
- No other field, route, session or token behaviour changes.

Use-case path: `UpdatePreferencesCommand.disclaimers: bool | None`; `UpdatePreferencesService` includes it in the "nothing to change" test and passes it to `PreferencesRepository.update_preferences`; `MePreferencesResult.disclaimers: bool`.

## Ui

| Piece | Behaviour |
|---|---|
| `MePreferences.disclaimers` | boolean from `GET /api/auth/me` (the BFF route passes the body through unchanged) |
| `usePreferences().setDisclaimers(next)` | `PATCH /api/auth/me { disclaimers: next }`; updates `me` on success; rejects when it cannot be saved, like `setTheme` |
| Account settings panel (`SidePanelSettings`) | a labelled switch "Show disclaimers" (Spanish: "Mostrar avisos") below Theme and Language; the label and a short hint ("Show a reminder to check recipes read from pictures") come from `ui/lib/i18n/account.ts`; a failed save shows the same inline error pattern as the theme (`saveThemeFailed`) with a new `saveDisclaimersFailed` |
| Picture draft toast | shown when `me.disclaimers` is true; not shown when false; waits for `ready` and does not guess while preferences load |

The option is not cached in `localStorage` (the theme is cached only to avoid a flash; a toast has no such need), and sign-out discards `me` as it does today.

## Toast (existing component), change

`Toast` gains optional `durationMs?: number`. `show` uses it in place of `TOAST_MS` for a non-persistent toast. Default behaviour and all existing callers are unchanged. The picture toast: `{ id: "picture-disclaimer", text: t.pictureDisclaimer, durationMs: 10_000 }`, closable by tap, as every non-persistent toast already is.

## Wording (en / es)

| Key | English | Spanish |
|---|---|---|
| `pictureDisclaimer` | "This draft was read from a picture and may contain mistakes. Check the title, servings, ingredients and steps against the page." | "Este borrador se leyó de una imagen y puede tener errores. Revisa el título, las porciones, los ingredientes y los pasos con la página." |
| `disclaimersLabel` | "Show disclaimers" | "Mostrar avisos" |
| `disclaimersHint` | "Show a reminder to check recipes read from pictures." | "Mostrar un recordatorio para revisar las recetas leídas de imágenes." |
| `saveDisclaimersFailed` | "We couldn't save that setting. Try again." | "No pudimos guardar ese ajuste. Inténtalo de nuevo." |
