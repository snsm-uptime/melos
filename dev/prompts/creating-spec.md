For the other open questions I'm going with my recommendations: Python 3.12, roles Owner and Member, and copying the finance scaffold into this repo. Tell me if you want any of them different.

## 1. System view

```
Browser
  │  same-origin (I'll manage nginx on the server later)
  ▼
ui  (Next.js 16, App Router, BFF at /api/* → api)        ← reused
  │  cookie forwarded
  ▼
api (FastAPI, hexagonal)                                 ← reused shell
  ├─ domain/        pure rules, no I/O
  ├─ application/   use cases + ports
  ├─ adapters/      Gemini · web fetch · PDF · Postgres · SMTP
  └─ api/routes/    HTTP
  │
  ▼
db  (pgvector/pgvector:pg16)    ← only change: Postgres image with pgvector
```

It stays at **three services**, the same as finance's rule of only `db`, `api` and `ui`. There's no job queue: the slowest call, capturing a recipe, takes a few seconds, so a spinner is enough.

## 2. API layers

| Layer          | New modules                                                                                                                                                                                                                            |
| -------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `domain/`      | `recipe.py` (Unit, Size, Dimension, validation rules) · `cart.py` (scale + consolidate, pure) · `ingredient_catalog.py` (name normalization) · `toon.py` (encoder for our fixed shapes) · `render.py` (`to_markdown`, `to_embed_text`) |
| `application/` | `ports.py` + `RecipeExtractor`, `Embedder`, `ChatModel`, `PageFetcher`, `PdfRenderer` · use cases: `capture_recipe`, `recipes`, `carts`, `shopping_list`, `conversations`, `exports`                                                   |
| `adapters/`    | `llm/gemini.py` (extract, chat, embed) · `web/jsonld.py` · `pdf/weasyprint.py` + `templates/` + `fonts/` (Noto) · `persistence/` (SQLAlchemy, Alembic, pgvector) · `email/` (reused)                                                   |
| `api/routes/`  | `kitchens`, `invites`, `recipes`, `ingredients`, `categories`, `sources`, `carts`, `conversations`, `messages`, `exports` + reused auth routes                                                                                         |

Finance's "lists" become **Kitchens**. Membership checks, invites and access rules carry over almost unchanged. Every table has a `kitchen_id`, and access is checked in `application/`, the same way as finance's `list_access`.

## 3. The four key flows

**A. Capture a recipe: draft first, then confirm**
```
input: text | URL | photo
  → Source row (type, url?, raw text)
  → URL: fetch page → has schema.org Recipe JSON-LD? → map it directly
                                                no → send page text to Gemini
  → Gemini extractor, also given the Kitchen's ingredient catalog as TOON
      returns ParseResult{is_recipe, reason, draft}
      each ingredient: {catalog_name | proposed_new_name, ...}
  → domain checks the rules (size only for count units, vague notes have no quantity, 3–5 categories)
  → DRAFT returned to the UI, nothing saved yet
  → user reviews and edits → POST /recipes → save + create new catalog entries + embed
```
The draft step is the most important change from the Streamlit version. A wrong AI result costs one click to fix, not a delete and redo.

**B. Ask**
```
question + @mentioned recipe ids
  → embed the question → pgvector top-5 within this Kitchen
  → context = mentioned ∪ top-5, as TOON; plus the last ~6 messages
  → Gemini answers with {answer, found: bool, cited_recipe_ids}
  → check: cited ids ⊆ context ids, otherwise drop the ids that aren't
  → save the user message and the assistant message, with citations
```

**C. Shopping list:** the Cart lives in Postgres (one per Kitchen, so the couple shares it). `domain/cart.py` builds the consolidated list on every read. It's derived data, so it's never stored.

**D. PDF:**
```
Recipe or ShoppingList
  → Markdown from a Jinja2 template
  → HTML (markdown-it-py) + CSS with @font-face (bundled Noto Sans/Serif)
  → WeasyPrint → PDF streamed back
```
WeasyPrint needs `pango` installed in `api/Dockerfile`, which is fine because we build the image ourselves.

## 4. Data model (core tables)

```
kitchen(id, name, content_language)          ← en|es; sets canonical names + prompt language
membership(kitchen_id, user_id, role)        ← owner|member
ingredient(id, kitchen_id, name, dimension_hint)          unique(kitchen_id, name)
category(id, kitchen_id, name)                            unique(kitchen_id, name)
source(id, kitchen_id, type, url, raw_text, created_at)   type: text|url|photo
recipe(id, kitchen_id, source_id, title, base_servings, created_by, timestamps)
recipe_ingredient(id, recipe_id, ingredient_id, quantity, unit, size, preparation, vague_note, position)
recipe_category(recipe_id, category_id)
step(id, recipe_id, position, text)
recipe_embedding(recipe_id, model, embedding vector(768), updated_at)
cart(id, kitchen_id, people)   cart_item(cart_id, recipe_id, meals)
conversation(id, kitchen_id, user_id, title, archived_at)
message(id, conversation_id, role, content, cited_recipe_ids, created_at)
```

Choices built into this model:
- **Embeddings get their own table.** Switching embedding model means re-embedding, not migrating the recipe table.
- **The ingredient catalog is per Kitchen.** A shared global catalog would leak names between households and needs moderation.
- **`content_language` lives on the Kitchen.** The UI is English, but a couple can keep Spanish recipes, and ingredient names still merge because the whole Kitchen uses one language.
- **Conversations belong to a user, not the Kitchen.** Archive and delete are personal; reading recipes is shared.

## 5. AI errors

The Gemini adapter turns SDK exceptions into domain errors, and each maps to one HTTP status that the UI shows as a friendly message:

| Domain error      | HTTP                | UI message (sketch)                         |
| ----------------- | ------------------- | ------------------------------------------- |
| `AIQuotaExceeded` | 429 + `Retry-After` | "Limit reached, try again in a minute"      |
| `AIUnavailable`   | 503                 | "The assistant is down, your text is kept"  |
| `AIInvalidOutput` | 422                 | "Couldn't read that recipe, try rephrasing" |
| `NotARecipe`      | 422                 | "That doesn't look like a recipe"           |

The Gemini model names (chat and embedding) go in settings, not in code. `GEMINI_API_KEY` lives only in `.env`.

## 6. Testing

1. **Domain:** pure pytest for cart consolidation, the TOON encoder and the recipe rules. The old acceptance criteria 2–4 live here.
2. **Application:** use cases run against fake ports (`FakeExtractor`, `FakeEmbedder`), so no network or quota is used.
3. **Integration:** finance's compose test overlay running against Postgres with pgvector.
4. **AI evaluation:** a small set of example recipe texts, URLs and photos with expected drafts, run by hand. It isn't in CI because it uses quota. It doubles as evidence for the rubric's "Prueba y mejora" criterion.

## 7. Hosting

My recommendation is **finance's `docker-compose.prod.yml` on your homelab, exposed through a free Cloudflare Tunnel**. Same images, nothing new to learn. The backup is an always-free cloud VM (e.g. Oracle Cloud's free tier) running the same compose file, if you don't trust homelab uptime for grading day. Either way, add an uptime check on `/health`.

## Decisions to confirm before I write the PRD

1. **Draft-then-confirm for capture** (the recipe isn't saved until the user reviews it)? I recommend yes.
2. **Per-Kitchen ingredient catalog** plus **`content_language` on the Kitchen**?
3. **Cart shared per Kitchen**, and **conversations personal per user**?
4. **Hosting:** homelab + Cloudflare Tunnel, or a free VM?

Once you confirm, I'll rewrite `dev/docs/prd.md` in your four sections, with the entity/CRUD matrix, acceptance criteria and prompt texts as appendices. Then I'll update `AGENTS.md`, which still describes the Streamlit setup.
