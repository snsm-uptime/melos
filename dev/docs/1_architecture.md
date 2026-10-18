# 1. Architecture

> See main PRD at [prd.md](prd.md)

### 1.1 Stack and services

The project reuses the architecture, structure and tooling of [`snsm-uptime/finance-dashboard`](https://github.com/snsm-uptime/finance-dashboard).

```
Browser
  │  same-origin (localhost:3000 in development)
  ▼
ui   Next.js 16 (App Router, React 19, Tailwind 4) — BFF at /api/* → api
  │  session cookie forwarded
  ▼
api  FastAPI, Python 3.12, uv — hexagonal: domain | application | adapters | api
  │
  ▼
db   PostgreSQL 16 + pgvector (image pgvector/pgvector:pg16)
```

- **Three services only:** `db`, `api` and `ui`. No queue and no worker. The slowest call (capturing a recipe) takes a few seconds, so the UI shows a progress state.
- **Python:** 3.12 and `uv` only. Never use `pip` or `requirements.txt`.
- **Language:** English for code, documentation and UI. Recipe *content* may be English or Spanish (see `kitchen.content_language`).

### 1.2 What is reused from finance-dashboard

| Area | Reused as is | Adapted |
|---|---|---|
| Repo layout | `api/` (hexagonal), `ui/`, `scripts/`, `.github/workflows/ci.yml`, `.cursor/worktrees.json` | Project name, env prefix `FH_` → `MELOS_`, data dir `~/melos` |
| Compose | `docker-compose.yml` + `dev`, `prod`, `test`, `worktree`, `worktree-lite` overlays | `db` image → `pgvector/pgvector:pg16`; add `GEMINI_*` variables |
| Scripts | `compose-up/down/restart/wipe-db.sh`, `compose-lib.sh`, `worktree/*` | Names and default ports only |
| Lists + membership + invites | Membership checks, list access checks, invite-by-email flow | "List" becomes **Kitchen** |
| Authentication | The whole layer, see 1.3 | Names only (cookie `melos_session`, env prefix) |
| UI shell | `AppShell`, `AccountMenu`, `ActionDialog`, `Chip`, `ChipPicker`, `IconButton`, `Disclosure`, `CopyButton` and the Tailwind theme | Remove the language toggle (UI is English only) |
| Tooling | ruff, pytest, vitest, eslint, Alembic | — |

Do **not** copy finance's `.env.example` seed credentials or any finance domain code (cards, statements, budgets, splits, FX, bank adapters).

### 1.3 Authentication layer (reused)

The authentication layer comes from finance-dashboard with its behaviour unchanged. It is the security base of the app, so changes to it need explicit approval.

| Capability | Behaviour | Endpoint |
|---|---|---|
| Sign up | Email + password. Email is normalized (trimmed, lower-cased) and shape-checked. Password is 8–256 characters. An optional `invite_token` lands the new user in the inviting kitchen. On sign up, the user gets a personal kitchen ("My kitchen") | `POST /auth/register` |
| Sign in | Email + password. The same generic error for an unknown email and a wrong password | `POST /auth/sign-in` |
| Sign out | Revokes the session and clears the cookie | `POST /auth/sign-out` |
| Session | Opaque session token stored in Postgres. httpOnly cookie, `SameSite=Lax`, `Secure` in production. **The api is the only cookie issuer**; the ui BFF forwards `Set-Cookie` | `GET /auth/session` |
| Password storage | argon2 (`argon2-cffi`) | — |
| Password reset (signed out) | Email with a single-use token, stored hashed, valid for 1 hour. The request answers the same whether or not the email exists | `POST /auth/password-reset/request`, `/confirm` |
| Password change | There is no separate signed-in change form. `/account` links to the reset flow above, as in finance. The new password goes through the same validation as sign up | (reset endpoints) |
| Email verification | Behind the `EMAIL_VERIFICATION_REQUIRED` setting (default `false`). When `true`, accepting an invite requires a verified email. It is not a login wall | `POST /auth/verify/request`, `/confirm` |
| Profile | Alias (set once), photo (size-capped, validated in the domain), theme (`light`/`dark`/`system`) | `GET/PATCH /auth/me` |
| Rate limits | Per IP and per user on register, sign-in, password reset and verification. `429` with `Retry-After`. The BFF passes the client IP in a header that the api trusts only from `TRUSTED_PROXY_IPS` | — |
| Email | SMTP (`aiosmtplib`). Bad SMTP settings **fail loudly**, never a silent success | — |
| UI pages | `/sign-up`, `/sign-in`, `/forgot-password`, `/reset-password`, `/verify`, `/invites/accept`, `/account` | — |

### 1.4 API layers

| Layer | Modules |
|---|---|
| `domain/` (pure, no I/O) | `recipe.py` (Unit, Size, Dimension, validation rules) · `cart.py` (scale + consolidate) · `ingredient_catalog.py` (name normalization, merge rules) · `toon.py` (TOON encoder for our fixed shapes) · `render.py` (`to_markdown`, `to_embed_text`) · `kitchen.py`, `membership.py`, `invite.py` (from finance's lists) |
| `application/` | `ports.py`: `RecipeExtractor`, `Embedder`, `ChatModel`, `PageFetcher`, `PdfRenderer`, repositories · use cases: `capture_recipe`, `recipes`, `ingredients`, `categories`, `carts`, `shopping_list`, `conversations`, `exports`, `kitchens`, `invites` + reused auth use cases |
| `adapters/` | `llm/gemini.py` (extract, chat, embed — `google-genai` SDK) · `web/page_fetcher.py` + `web/jsonld.py` · `pdf/weasyprint.py` + `templates/` + `fonts/` · `persistence/` (SQLAlchemy, Alembic, pgvector) · `email/` (reused) |
| `api/routes/` | `auth` (reused), `kitchens`, `members`, `invites`, `recipes`, `drafts`, `ingredients`, `categories`, `sources`, `carts`, `shopping-list`, `conversations`, `messages`, `exports`, `health` |

Every table except auth tables has a `kitchen_id`. Access is checked in `application/`, the same way finance checks list access. A user who is not a member gets `404`, not `403`, so the response doesn't reveal that the kitchen exists.

### 1.5 Key flows

**A. Capture a recipe (draft first, then confirm)**
```
input: text | URL | photo
  → URL: PageFetcher (SSRF-safe, see 1.7) → schema.org/Recipe JSON-LD present?
        yes → map it to a RecipeDraft (ingredient lines still go to Gemini for normalization)
        no  → visible page text → Gemini
  → photo: image → Gemini (multimodal); the image is not stored
  → Gemini RecipeExtractor, given the kitchen's ingredient + category catalog as TOON
        returns ParseResult{is_recipe, reason, draft}
  → domain checks the rules; anything that fails → AIInvalidOutput
  → the DRAFT is returned to the UI; nothing is saved
  → user reviews and edits → POST /recipes
        → save the Source, Recipe, lines and steps; create the confirmed new ingredients/categories; embed
```

**B. Ask**
```
question + @mentioned recipe ids
  → embed the question → pgvector top-5 within this kitchen (cosine)
  → context = mentioned ∪ top-5, as TOON; plus the last 6 messages
  → Gemini ChatModel → {answer, found, cited_recipe_ids}
  → drop any cited id that is not in the context
  → save the user message and the assistant message with its citations
```

**C. Shopping list.** The cart is stored per kitchen. `domain/cart.py` builds the consolidated list on every read. It is derived data and never stored.

**D. PDF.**
```
Recipe | ShoppingList → Markdown (Jinja2 template) → HTML (markdown-it-py)
  → CSS with @font-face, bundled Noto Sans + Noto Serif → WeasyPrint → PDF bytes
```
The PDF template reads the domain model, not TOON. `api/Dockerfile` installs WeasyPrint's system libraries (pango). Fonts live in `adapters/pdf/fonts/`, not in system fonts, so English, Spanish (á é í ó ú ü ñ ¿ ¡) and fractions (½ ⅓ ¼ ¾ ⅔) always render.

**E. Serializations from one source of truth**
```
Postgres → domain Recipe
  ├─ to_toon()        → LLM context (extraction catalog, chat context)
  ├─ to_embed_text() via EmbedTextStrategy → pgvector
  └─ to_markdown()    → PDF template, Markdown copy
```
Embeddings are generated via the `EmbedTextStrategy` port (Strategy pattern), defaulting to TOON format for consistency with Gemini's chat context. The strategy is swappable to A/B test approaches (e.g., TOON vs. plain text). Each `recipe_embedding` records which strategy was used, input token count, and creation date to measure differences in search quality and token efficiency. The TOON encoder follows `dev/skills/using_toon.md` and is tested against its examples.

**F. Vector search filtering.** Before pgvector similarity search, SQLAlchemy pre-filters recipes by: `kitchen_id` (required), `created_by` (optional, for "my recipes" view), `created_after`/`created_before` (date range), `ingredient_ids` (recipes containing specific ingredients), `category_ids` (optional), and `exclude_recipe_ids` (e.g., to avoid re-citing @mentioned recipes). The filtered set then undergoes cosine similarity search, limited to the top 5 results.

### 1.6 Data model

```
kitchen(id, name, content_language: en|es, created_at)
membership(kitchen_id, user_id, role: owner|member, created_at)       pk(kitchen_id, user_id)
invite(id, kitchen_id, email, token_hash, invited_by, expires_at, accepted_at)
ingredient(id, kitchen_id, name, created_at)                          unique(kitchen_id, name)
category(id, kitchen_id, name)                                        unique(kitchen_id, name)
source(id, kitchen_id, type: text|url|photo, url, raw_text, created_at)
recipe(id, kitchen_id, source_id?, title, base_servings ≥ 1, servings_estimated,
       created_by, created_at, updated_at)
recipe_ingredient(id, recipe_id, ingredient_id, quantity?, unit?, size?, preparation?,
                  vague_note?, position)
recipe_category(recipe_id, category_id)
step(id, recipe_id, position, text)
recipe_embedding(recipe_id, model, embedding vector(768), strategy_used, input_tokens, updated_at)  pk(recipe_id, model)
cart(id, kitchen_id unique, people ≥ 1)
cart_item(cart_id, recipe_id, meals ≥ 1)                               pk(cart_id, recipe_id)
conversation(id, kitchen_id, user_id, title, archived_at?, created_at, updated_at)
message(id, conversation_id, role: user|assistant, content, found?, cited_recipe_ids[], created_at)
+ auth tables reused from finance (user, session, password_reset_token, email_verification, preferences)
```

**Value sets**
- `Unit`: `g, kg, oz, lb, ml, l, cup, tbsp, tsp, unit`
- `Size`: `small, medium, large`, only when `unit = unit`
- **Dimension** is derived from the unit, never stored and never chosen by the AI:
  - mass: `kg > lb > oz > g`
  - volume: `l > cup > tbsp > tsp > ml`
  - count: `unit`

**Line rules (enforced in `domain/recipe.py`)**
- `vague_note` set → `quantity` and `unit` are null.
- `size` is only allowed when `unit = unit`.
- A non-vague line needs both `quantity > 0` and `unit`.

**Normalization**
- Ingredient and category names are trimmed, lower-cased and singular. Preparation never goes in the name ("onion" + `preparation: "chopped"`).
- Categories are de-duplicated, with 3–5 per recipe.

**Design choices**
- Embeddings live in their own table, so switching models means re-embedding, not migrating.
- The ingredient catalog is per kitchen: no leaking between households, no moderation needed.
- `content_language` on the kitchen fixes the language of canonical names, so ingredients merge on the shopping list.
- The cart is shared per kitchen. Conversations are personal per user.

### 1.7 AI integration, errors and safety

**Configuration** (in `.env`, never in code or the repo):
- `GEMINI_API_KEY`
- `GEMINI_CHAT_MODEL` (`gemini-2.5-flash-lite`)
- `GEMINI_EMBED_MODEL` (`gemini-embedding-2`)
- `GEMINI_EMBED_DIM` (768)

**Structured output.** The extractor and the chat use `response_schema` built from Pydantic models, kept flat (no complex unions) because Gemini supports only part of JSON Schema.

**Error mapping.** The Gemini adapter turns SDK exceptions into domain errors. The api maps each to one status, and the UI shows a plain message:

| Domain error | HTTP | UI message |
|---|---|---|
| `AIQuotaExceeded` | 429 + `Retry-After` | "We've hit the assistant's limit. Try again in a minute." |
| `AIUnavailable` (timeout, network, 5xx) | 503 | "The assistant isn't responding. Your text is kept — try again." |
| `AIInvalidOutput` (schema or domain rule failed) | 422 | "We couldn't read that recipe. Try rephrasing or adding detail." |
| `NotARecipe` | 422 | "That doesn't look like a recipe." + the reason |
| `PageFetchFailed` / `PageBlocked` | 422 | "We couldn't open that page. Paste the recipe text instead." |

The user's input (text, URL or photo) is never lost on error.

**URL fetching (SSRF protection)**
- `http`/`https` only.
- The resolved IP must not be private, loopback, link-local or a cloud metadata address. This is checked again after every redirect, with at most 3 redirects.
- 10 s timeout, 2 MB size limit, HTML only.

**Prompt injection.** Imported pages and recipe text are data. Prompts wrap them in delimited blocks and tell the model to ignore instructions inside them (Appendix B).

### 1.8 Testing

1. **Domain:** pure pytest. Cart consolidation, line rules, normalization, TOON encoder, Markdown render.
2. **Application:** use cases against fake ports (`FakeExtractor`, `FakeEmbedder`, `FakeChatModel`, `FakePageFetcher`), so no network and no quota.
3. **Integration:** finance's compose test overlay against Postgres with pgvector. Covers routes, membership checks, CRUD and the reused auth tests.
4. **UI:** vitest for clients and components, as in finance.
5. **AI evaluation (manual, not in CI):**
   - `api/tests/fixtures/ai_eval/` holds about 10 inputs: texts, URLs saved as HTML, photos, one non-recipe and one with two recipes.
   - Each has its expected draft.
   - The results are the evidence for the "test and improve" part of the course submission.

### 1.9 Deployment

- **Local development** uses the compose scripts only (`./scripts/compose-up.sh`), with `ui` on `localhost:3000` and `api` on `localhost:8000`. No reverse proxy.
- **Production** runs `docker-compose.yml` + `docker-compose.prod.yml` on the owner's server. The reverse proxy (nginx), TLS and anything else on the server are set up later by the owner, outside this repo, and are **out of scope** for this spec.
- Postgres data lives under `MELOS_DATA` on the host, outside the repository.
- The public URL must work on grading day; `/health` on `ui` and `api` is what to check.
