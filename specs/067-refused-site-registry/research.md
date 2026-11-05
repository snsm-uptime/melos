# Research: Refused Site Registry

## R1 Which answers count as a refusal

- **Decision**: The final response (after redirects) has status 401, 402, 403 or 451.
- **Rationale**: These are the statuses where a site deliberately denies access: 402 is People Inc./Cloudflare's licensing wall (seen on allrecipes.com on 2026-11-04), 403 is the usual bot block, 401 asks for an account, and 451 is a legal block. 404, 410, 429 and 5xx are a missing page, a rate limit or a fault, not a license matter.
- **Alternatives**: Every 4xx (too broad, because a 404 would be called "needs a license"). Matching body text such as "licensing" (fragile, and different on every site).

## R2 Keeping the network unprobeable (spec 026 R10)

- **Decision**: Only a real HTTP answer from a host that passed the SSRF checks can become `refused`. `blocked`, `dns`, `connect`, `timeout` and the rest are unchanged and still map to `page_fetch_failed`.
- **Rationale**: A refusal comes from a public host that actually answered, so its own code tells the member nothing about internal addresses.

## R3 Registrable domain

- **Decision**: Use `tldextract.TLDExtract(suffix_list_urls=())`, which uses the bundled public-suffix snapshot and never makes a network call at runtime. The result is lower-cased `domain.suffix`. When there is no suffix (an IP literal can't get here, but as a fallback), use the host as is.
- **Rationale**: This handles `www.`/`m.` subdomains and multi-part suffixes (`bbc.co.uk`). Writing our own reduction gets `co.uk` wrong.
- **Alternatives**: Stripping `www.` only (misses `m.`, `es.` and others). Downloading the live suffix list (that is a network call outside `PageFetcher`).
- **Placement**: In the persistence adapter, because domain/ allows no third-party imports.

## R4 Distinct members without storing who

- **Decision**: Use `refused_site_member(domain, member_key)` with a unique pair. `member_key = HMAC-SHA256(k, domain || user_id)`, where `k = HMAC-SHA256(SESSION_SECRET, "melos-refused-site-v1")`. `distinct_members` is incremented only when the insert actually added a row (`ON CONFLICT DO NOTHING`, rowcount 1).
- **Rationale**: Neither table holds a user id. Without the server secret, nobody can link a key to an account, not even by trying every known user id. Including the domain in the key means the same person can't be traced across domains. `SESSION_SECRET` is only read; the auth layer is unchanged.
- **Consequence**: Rotating `SESSION_SECRET` starts the distinct counts over for members seen again, which is acceptable for a demand signal. Totals stay the same.
- **Alternatives**: Storing user_id (rejected by FR-007). A plain SHA-256 of the user id (reversible by trying every account). A new `REFUSED_SITE_KEY` env var (more config for little gain).

## R5 The site's message

- **Decision**: On a refusal status, the fetcher reads at most 64 KB of the body (separate from the 2 MB page limit) and stays within the same deadline. A stdlib `html.parser` subclass drops `script`, `style`, `noscript` and `template` content, keeps text and link targets for `mailto:` (so "contact support@people.inc" survives), unescapes entities and collapses whitespace. The result is trimmed to 1,000 characters on a word boundary, and an empty result is stored as `""`. A body that isn't text/html, or a read failure, also gives `""`.
- **Rationale**: Licensing contacts are the useful part for the admin. html.parser needs no new dependency, and trafilatura is built for articles and drops short pages.

## R6 Recording must not affect the member

- **Decision**: The use case calls `RefusedSiteLog.record(...)` inside `try/except Exception`. On failure it logs `refused site record failed: host=…` and still returns the `PageFetchFailed("refused")`. The adapter uses a SAVEPOINT (`session.begin_nested()`), so a failed insert doesn't poison the request's session.
- **Concurrency**: `INSERT … ON CONFLICT (domain) DO UPDATE SET total = total + 1 …` gives the race in the edge cases one row with count 2.

## R7 API and UI codes

- **Decision**: Return `422 {"code":"site_requires_license","detail":""}`. The UI strings are en "This website requires a license, it's not supported yet." and es "Este sitio web requiere una licencia, aún no es compatible." The admin dashboard gets section `refused-sites`, and its message cell is rendered as a React text node (escaped), never as HTML.
