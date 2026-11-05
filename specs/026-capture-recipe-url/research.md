# Research: Capture a Recipe from a URL (spec 026)

Each item: Decision, Rationale, Alternatives considered. Code references are as of 2026-11-04 on `worktree-26` (HEAD 5e83bbc).

## R1. HTTP client for the page and the photo

**Decision**: Use `httpx` (0.28.1), already in `api/uv.lock` as a dependency of `google-genai`, declared as a direct dependency with `uv add httpx` so it no longer arrives only by accident. Client options: `follow_redirects=False` (redirects are followed by hand, R3), `trust_env=False` (no proxy or `.netrc` from the environment can bypass the address pin), no cookie jar kept between requests, a fixed `User-Agent: MelosRecipeImport/1.0`, `Accept: text/html,application/xhtml+xml` for the page and `image/jpeg,image/png,image/webp` for the photo.

**Rationale**: No new package enters the lock file. httpx streams the body (size cap, R4) and accepts the `sni_hostname` request extension that the address pin needs (R2).

**Alternatives**: `urllib.request` (no streaming size control per chunk without extra code, and no clean SNI override); `requests` (new package, same pin problem); trafilatura's own `fetch_url` (no address checks, rejected for safety).

## R2. Address checks and the pin against DNS rebinding (FR-007)

**Decision**: For each request (page, each redirect, photo):
1. Parse the URL and apply the link rules in `domain/page_link.py` (R5).
2. Resolve the host with `socket.getaddrinfo` in a worker thread bounded by the remaining deadline (getaddrinfo has no timeout of its own).
3. Refuse when **any** resolved address fails `domain.page_link.is_public_address`: the address, or its embedded IPv4 (`ipv4_mapped`, 6to4 and Teredo forms), must be `ipaddress.ip_address(...).is_global` and not multicast. `is_global` is false for loopback, RFC 1918, link-local (169.254.0.0/16, so 169.254.169.254), CGNAT 100.64.0.0/10, unspecified, reserved, documentation and ULA ranges (fd00:ec2::254 included). An IP literal host is checked the same way without DNS.
4. Connect to the first checked address: the request URL carries the IP literal, the `Host` header carries the original host, and the `sni_hostname` extension carries the original host, so TLS checks the certificate against the real name. No second resolution happens.

**Rationale**: Checking every resolved address and connecting to the checked one closes the time-of-check/time-of-use gap. `is_global` is the stdlib's maintained list, so the code does not keep its own range table. The check is pure (stdlib `ipaddress`, no I/O) and lives in `domain/`.

**Alternatives**: A custom httpx transport that resolves inside connect (more code inside httpcore internals); an egress proxy (a new service, forbidden by constitution principle 1).

## R3. Redirects (FR-008)

**Decision**: Follow 301, 302, 303, 307 and 308 by hand, at most 3. Each `Location` is resolved against the current URL, then goes through R5 and R2 again. A fourth redirect, a missing `Location`, or a refused target ends the fetch as `PageFetchFailed(kind="redirect")` or `kind="blocked"`. The final URL after redirects is what the draft returns and what Save stores (FR-019).

**Rationale**: Automatic redirects would skip the address check on the new host.

## R4. Limits and content checks (FR-009, FR-005a)

**Decision**:
- One deadline per fetch, measured with `time.monotonic()`: 10 s for the page (DNS, connect, every redirect and the body together), 5 s for the photo. httpx `Timeout` gets the remaining time on each request, and the body loop checks the deadline between chunks.
- Body read with `iter_bytes()`, stopping as soon as the running total passes 2 MB, whatever `Content-Length` says. A `Content-Length` above 2 MB ends the fetch before the body is read.
- Status: only 2xx (after redirects). 401, 402, 403, 404, 410, 429 and 5xx end as `PageFetchFailed`.
- Page type: `Content-Type` `text/html` or `application/xhtml+xml`. Others (PDF, images, JSON) end as `kind="not_html"`.
- Photo type: decided by the first bytes (JPEG `FF D8 FF`, PNG `89 50 4E 47`, WebP `RIFF....WEBP`), not by the header alone. Anything else is dropped.
- Charset: from the `Content-Type` header, else the first `<meta charset>` in the first 2 KB, else UTF-8; decoded with `errors="replace"`.

**Rationale**: Matches PRD §1.7 and constitution principle 4 exactly, with the photo kept tighter so it never adds to the member's wait (R9).

## R5. Link rules before any request (FR-003, FR-006, edge cases)

**Decision**: `domain/page_link.py` holds pure functions:
- `normalize_link(raw)`: trim; refuse empty, longer than 2,048 characters, or containing whitespace inside; add `https://` when the text has no scheme; lower-case the scheme and host; IDNA-encode the host.
- `check_link(url)`: scheme `http` or `https`; no user name or password; port absent, 80 or 443 (Clarifications Q3); a host is present. Returns the parsed parts or raises `PageLinkRefused(kind)`.

The ui runs the same rules in `ui/lib/capture/linkRules.ts` only to enable the button and show the field messages; the api is the authority.

## R6. Reading the page: schema.org data, main photo and Markdown (FR-011, FR-012, FR-005a)

**Decision**: A new port `PageReader` with one adapter, `adapters/web/page_reader.py`, that turns HTML into `PageContent`:
- **schema.org Recipe** (`adapters/web/jsonld.py`): the stdlib `html.parser` collects every `<script type="application/ld+json">` block; each is parsed with `json.loads` (a block that fails to parse is skipped). The pure domain function `domain.recipe_page.recipes_from_jsonld(objects)` walks lists and `@graph`, keeps nodes whose `@type` is `Recipe` or a list containing it, and maps each to `PageRecipe(title, yield_text, ingredients, steps, image_urls)`. Instructions: a string (split on line breaks), `HowToStep.text` (or `name`), `HowToSection.itemListElement` in order (flattened, FR-015); HTML tags and entities are stripped from every string.
- **Main photo**: the first `image` of the chosen Recipe item (a string, a list, or an `ImageObject.url`); else the first `<meta property="og:image">`. Resolved against the final page URL.
- **Markdown**: `trafilatura.extract(html, output_format="markdown", include_tables=True, include_formatting=True, include_comments=False, include_images=False, include_links=False, favor_recall=True, deduplicate=True)`. trafilatura finds the main content and drops navigation, headers, footers, comments, forms and ads, which is what FR-012 asks for. `include_links=False` keeps link text only. If it returns nothing, the page has no readable text.

**New library**: `trafilatura` 2.3.1, Apache-2.0 (checked on PyPI 2026-11-04). It brings `lxml`, `justext`, `htmldate`, `courlan`, `charset_normalizer` and `urllib3`. Its own downloader is never called (R1). **Approved by the owner on 2026-11-04**; added with `uv add trafilatura` (AGENTS.md, "If you add a library, say so").

**Rationale**: Main-content extraction is the hard part of "drop ads, comments and navigation"; trafilatura is built for it and writes Markdown directly. JSON-LD parsing stays in the stdlib and pure domain code, so AC2.3 does not depend on the new library.

**Alternatives**: `markdownify` + `beautifulsoup4` (converts everything, so comments, menus and ads stay; boilerplate removal would be hand-written); `readability-lxml` + `markdownify` (two libraries, weaker on recipe blogs); a hand-written `html.parser` converter (no main-content detection).

## R7. Recipe from schema.org data (FR-011, AC2.3)

**Decision**: When exactly one `PageRecipe` has at least one ingredient, the use case writes a short Markdown text from it (title, servings text, the ingredient list, the numbered steps) and calls the extractor in whole-recipe mode, with the notebook's catalog, exactly like text capture. On a `Draft`, `domain.recipe_page.apply_page_recipe(draft, page_recipe)` replaces the title and steps with the schema.org values, and the servings when `parse_yield(yield_text)` finds a whole number ≥ 1 (then `servings_estimated=False`). The result then goes through `check_draft` as usual. Two or more Recipe items → `NotARecipe(MULTIPLE_RECIPES)` without any call. One item with no ingredients → the Markdown path (R6).

**Rationale**: The ingredient rules (singular names, preparation, vague amounts, units, catalog match, unit questions of spec 055) stay in one place: the extractor plus `check_draft`. AC2.3 holds by construction, because title and steps are overwritten from the data.

**Alternatives**: Parse `recipeIngredient` strings in code (duplicates the extractor's rules and fails on Spanish phrasing); send the raw JSON-LD to the model (larger input, and the title or steps could drift).

## R8. Batches and the partial page mode (FR-013, FR-013a, FR-013b)

**Decision**:
- Settings: `RECIPE_PAGE_BATCH_CHARS` (default 10,000; must be ≥ 1,000 and ≤ the extraction use case's `MAX_TEXT_CHARS`, 10,000) and `RECIPE_PAGE_MAX_BATCHES` (default 4, 1 to 8).
- `domain.recipe_page.split_markdown(markdown, batch_chars, max_batches)` splits on blank lines (blocks) and, inside an over-long block, on line breaks; never inside a line, except a single line longer than a whole batch, which is cut at a space. Returns the batches and `cut: bool` (Markdown beyond the cap was dropped).
- One batch → whole-recipe mode, same as text capture.
- Several batches → **partial page mode**. The port gains a keyword `mode: ExtractionMode = ExtractionMode.WHOLE` and, for parts, `part=(index, total)`. In the Gemini adapter, partial mode uses its own system template `prompts/recipe_extraction_page_part_system.md` and response schema: outcome `recipe_part | no_recipe_content | multiple_recipes`; `recipe` with `title`, `base_servings`, `ingredient_lines`, `steps`, none required. The user turn is the same template with one more line, "Part {{PART}} of {{TOTAL}} of one web page." The line and safety rules are copied from the whole-recipe template, so the two stay in step (a characterization test compares the shared rule block).
- New result `DraftPart(title, base_servings, ingredient_lines, steps)` and `NoRecipeContent()`. `RecipeExtraction` does not run `check_draft` on a part.
- Batches run at the same time on a `ThreadPoolExecutor(max_workers=RECIPE_PAGE_MAX_BATCHES)` created per capture and closed at the end. Each is one attempt with the text timeout. The in-flight sharing key gains the mode and part, so a part never shares a whole-mode result.
- `domain.recipe_page.merge_parts(parts)` returns a raw `DraftRecipe` or a refusal: title from the first part with one; servings from the first part with them; lines and steps in batch order, dropping a line equal to an earlier one on (name, vague, quantity, unit, size, preparation, note) after trimming and lower-casing, and a step equal to an earlier one after whitespace folding; `MULTIPLE_RECIPES` when any part says so or when two parts each carry a title, lines and steps and their titles differ after folding case, accents and spaces; `NoRecipeContent` when every part says so. The merged draft then goes through `check_draft` (missing parts and line problems of spec 017).
- Any failed part (`Unavailable`, `LimitReached`, `InvalidOutput`, `AIProviderError`) fails the capture with that result; the first failure in batch order wins. Remaining futures are left to finish and their results dropped (each call has its own timeout).

**Rationale**: The owner asked for a partial page mode (2026-11-04). A separate template and schema keep the whole-recipe prompt, which text capture depends on, byte-for-byte unchanged. Merging is pure and testable without the model (SC-009).

**Threads and the constitution**: the pool lives inside one request and ends with it. It is not a queue or a background worker (principle 1), and `RecipeExtraction` already uses threads for in-flight sharing.

**Alternatives**: Sending the whole Markdown in one larger call (the owner chose batches); sequential batches (breaks SC-002 for 4 batches); asking the model to merge (another call and more cost).

## R9. The main photo (FR-005a, FR-019, Clarifications Q2)

**Decision**:
- Fetched by the same `PageFetcher` (`fetch_image`), with R2, R3 and R5 rules, 5 s and 2 MB, started as soon as the page is read so it runs while the extractor works. A failure returns `None` and is logged by kind only.
- The api returns it in the draft as a data URI (`preview_image`), never as the site's URL, so the browser never contacts the site (FR-019).
- The browser shrinks it before Save with a new `encodeRecipePreview` in `ui/lib/imageEncode.ts`: longest side 800 px, JPEG, quality stepped down until it fits 300 KB. This reuses the avatar approach ("the backend never needs an image library"), so no Pillow.
- Save accepts `preview_image` as a `data:image/jpeg|png|webp;base64,` URI of at most 300 KB decoded, checked by a new `domain.recipe_preview.validate_preview_image`, modelled on `domain/photo.py`.
- Stored in a new nullable column `recipe.preview_image_base64` (PRD §1.6 already names it); migration `0015_recipe_preview_image`. `copy_all` (spec 035 snapshots) copies it; edit (spec 027) keeps it; delete removes it with the row.

**Constitution principle 5**: amended to 2.0.0 on 2026-11-04. The MVP rule "Photos are not stored" is lifted; an image is stored only where a story says so, with a size limit and a format check, which this item gives (300 KB, JPEG/PNG/WebP). S-067 (recipe image upload) reuses the column and the check.

## R10. Error codes and messages (FR-021, FR-021a, FR-022)

**Decision**: New codes on `POST /notebooks/{id}/captures/url`: `link_empty`, `link_invalid`, `link_too_long` (422, before any work); `page_fetch_failed` (422, every fetch failure including blocked addresses, so a member cannot probe the network by message); `page_no_recipe` (422, FR-021a). Existing codes keep their meaning: `one_recipe_at_a_time`, `draft_incomplete`, `ingredient_line_problem`, `ai_invalid_output`, `ai_limit_reached` (429), `ai_unavailable`, `ai_misconfigured` (503), `notebook_not_found` (404), `kitchen_archived` (409). `not_a_recipe` is never sent by this route: a whole-mode `NotARecipe` other than multiple recipes becomes `page_no_recipe`.

**Narrowed by spec 067 (2026-11-04)**: when the public site itself answers 401, 402, 403 or 451, the route answers `422 site_requires_license` ("This website requires a license, it's not supported yet."), still with no status, domain or site text. A real answer from a host that passed the address checks reveals nothing about the network; every other failure, blocked addresses included, stays `page_fetch_failed`. See `specs/067-refused-site-registry/`.

UI messages live in `ui/lib/i18n/capture.ts` (English and Spanish; parity test). The assistant messages get link variants ("Your link is kept" / "Tu enlace se conserva"). Spanish wording is drafted and needs the owner's review, as in spec 063.

## R11. Timing (SC-002)

**Decision**: Page fetch ≤ 10 s, then schema.org or Markdown work (< 1 s for 2 MB), then the extractor calls in parallel ≤ `GEMINI_TEXT_TIMEOUT_S`, with the photo in parallel ≤ 5 s. The BFF route waits 10 + `GEMINI_TEXT_TIMEOUT_S` + 2 s before answering `ai_unavailable`. trafilatura runs in the request thread; a 2 MB page takes well under a second in published benchmarks, checked again in quickstart step 9.

## R12. Logging (constitution principle 4)

**Decision**: Log the outcome class, the fetch failure kind, the host only (never path or query, which can carry personal tokens), the page byte count, the Markdown length, the batch count and whether it was cut. Never the HTML, the Markdown, the photo or resolved addresses.

## R13. MCP reuse (FR-026)

**Decision**: The use case `CaptureRecipeUrl` takes a command (actor, notebook, link, language) and returns the same outcome types as text capture, with no HTTP types, so the S-032 capture tool can call it through the api later. Nothing is built in `mcp/` now.
