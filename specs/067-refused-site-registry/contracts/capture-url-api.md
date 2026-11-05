# Contract: `POST /notebooks/{id}/captures/url` (changed)

Adds one error. Every other answer is as in spec 026.

| Case | Status | Body |
|---|---|---|
| Site answered 401/402/403/451 | 422 | `{"code":"site_requires_license","detail":""}` |
| Any other fetch failure (incl. blocked, credentials, port) | 422 | `{"code":"page_fetch_failed","detail":""}` (unchanged) |

The body never holds the status, the site text, the domain or an address.

UI (`ui/lib/i18n/capture.ts`), `site_requires_license`:

- en: "This website requires a license, it's not supported yet."
- es: "Este sitio web requiere una licencia, aún no es compatible."
