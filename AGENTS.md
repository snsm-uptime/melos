# AGENTS.md · Melos

## What this project is

A shared home cookbook for a non-technical couple: it turns recipes from text,
web pages or cookbook photos into structured recipes, answers questions about
them, and builds a weekly shopping list scaled to the number of people.

The full specification is in `dev/docs/prd.md`. Read it before building
anything. If the spec and this file disagree, ask.

**→ Before starting work, read the [Project Constitution](.specify/memory/constitution.md) (`.specify/memory/constitution.md`).** It establishes the engineering principles, architectural boundaries, and non-negotiable rules that all contributors must follow.

## How it is built

The architecture, structure, auth layer and tooling are reused from
[`snsm-uptime/finance-dashboard`](https://github.com/snsm-uptime/finance-dashboard)
(see `dev/docs/prd.md` §1.2–1.3).

- **Four Compose services:** `db` (PostgreSQL 16 + pgvector), `api`
  (FastAPI, Python 3.12, uv), `ui` (Next.js 16, App Router, React 19,
  Tailwind 4), and `mcp` (FastAPI, Python 3.12, isolated for security).
  The ui is a BFF: the browser only talks to `ui`, which proxies
  `/api/*` to `api`. External AI providers (Claude, ChatGPT) reach the `mcp`
  service via `/mcp` endpoints with per-user API key authentication.
- **api is hexagonal:** `domain/` (pure rules, no I/O) → `application/` (use
  cases + ports) → `adapters/` (Gemini, web fetch, PDF, Postgres, SMTP) →
  `api/routes/` (HTTP).
- **AI:** Gemini API with the `google-genai` SDK, only through ports in
  `adapters/llm/`. Model names come from settings (`GEMINI_CHAT_MODEL`,
  `GEMINI_EMBED_MODEL`), never hard-coded.
- **Auth:** reused from finance-dashboard unchanged (session cookie issued by
  the api, argon2, password reset by email, config-gated email verification,
  rate limits).

## Domain rules

Source of truth: `dev/docs/prd.md` §1.6 and §2 J3.

- Recipes live in notebooks. A recipe is in exactly one notebook. Recipes and
  ingredients point at `notebook_id`; a copy finds its source and target by
  notebook id.
- There are two kinds of notebook (decided 2026-10-23, PRD §1.5 flow H;
  replaces the kitchen-owned notebook of 2026-10-22 and the kitchen links):
  - A **personal notebook** belongs to people: one owner, who created it, and
    any number of notebook members, who joined through a notebook invite (the
    kitchen invite flow, reused). The owner and members add, edit and delete
    its recipes; only the owner renames or deletes it and invites or removes
    members. It is never shown in a kitchen. Every person gets a default one,
    "{alias}'s Notebook", on first use (`users.default_notebook_id`; the auth
    routes are not changed) and can create more.
  - A **kitchen notebook** belongs to one kitchen, which can have several. Every
    member of the kitchen reads, writes, renames and deletes it, only while
    they belong to the kitchen. It has no owner and no membership rows. It is
    deleted with the kitchen.
- A kitchen notebook is created with the kitchen by the kitchen service, as
  "{alias}'s ({kitchen name}) Notebook" named after the creator; by the first
  capture in a kitchen that has none (for example "My kitchen", which signup
  makes); or as a snapshot. A snapshot is an independent kitchen copy of a
  personal notebook, added by any kitchen member. It keeps only an origin
  label (`source_notebook_id`, cleared if the original is deleted); the two
  never sync.
- A capture outside a kitchen goes into a personal notebook the person owns or
  is a member of; in a kitchen, into one of the kitchen's notebooks. With
  several, the person picks one. No capture happens in an archived kitchen.
- Leaving a kitchen ends access to its notebooks; nothing is copied. When an
  owner deletes their account, each personal notebook they own passes to its
  longest-standing member, or is deleted when it has none.
- Each notebook has its own ingredient catalog: a set of unique normalized
  names (trimmed, lower-case, singular), stored as plain strings. Recipe lines
  and shopping list lines carry the name, not an id. A new notebook's catalog
  starts from its owner's (or a kitchen notebook's creator's) names, and a
  snapshot copies the catalog; when someone joins a personal notebook, their
  names are matched against it, the notebook's names win, and the rest are
  added.
- Recipes move between notebooks only by copying (PRD §1.5 flow G): "Copy to
  notebook", from any recipe the person can read into a notebook they can
  write to, and snapshots of a whole personal notebook into a kitchen. A copy
  has no link to the original, and the two drift apart: editing or deleting
  one never changes the other.
- A copy's ingredient names are normalized against the target notebook's
  catalog, and the target's names take priority. The app tells the person
  which changes were made, before they confirm.
- A recipe records its author, the person who added it. Lists show the
  author's alias; if the author's account is deleted, it reads "unknown". A
  snapshot keeps each recipe's author. Author history is out of scope. Never store past
  owners or the recipe a copy came from.
- A recipe stores its categories as ids (no category table), editable on the
  recipe. Categories come only from the controlled lists in `dev/docs/categories.yaml`
  and `dev/docs/cuisine.yml`. They are never renamed or matched.
- When Gemini matches a name to an existing catalog entry (e.g. "onions" to
  "onion"), the app tells the member which changes were made, before save.
- Recipe preview images are stored as base64 text on the recipe. Captured
  source photos are not stored (PRD §4).
- Cart frequency counts every addition to the kitchen's cart, kept on the
  kitchen notebook's recipe. Removing a recipe from the cart does not lower it.

## Shared UI components

- **Add-recipe call to action** (`ui/components/AddRecipeCallToAction/`, to be
  created with S-016): the rounded-corner placeholder rectangle with a plus
  icon. Any page that lets a user add a recipe uses this component. Do not
  rebuild it on a page.
  - Tapping it opens the add-recipe options dialog: a vertical list separated
    by dividers, with no confirm or cancel buttons, in this order:
    1. URL: shown, disabled, not implemented yet.
    2. Picture: shown, disabled, marked "coming soon", until S-040.
    3. Text: opens the text sheet with the paste input and submit control.
  - Built on `ActionDialog` (its confirm and cancel props become optional so
    it can render without footer buttons) and `Sheet`. The picture sheet, when
    built, has an inner dashed border (about 2rem thick) with the text "Upload
    file or drag and drop".
  - Change the option list in this component only. Other pages get the change
    for free.

## Project structure

```text
.
├── AGENTS.md                  # Instructions for agents (this file)
├── CLAUDE.md, GEMINI.md       # Redirect to AGENTS.md
├── README.md                  # Guide for end users
├── .env.example               # Every variable, no real values
├── .env                       # Local secrets; NEVER committed
├── docker-compose.yml         # db | api | ui
├── docker-compose.{dev,prod,test,worktree,worktree-lite}.yml
├── scripts/                   # compose-*.sh and worktree/* helpers
├── .github/workflows/ci.yml
├── api/
│   ├── pyproject.toml, uv.lock, .python-version (3.12), Dockerfile, alembic.ini
│   ├── domain/                # Pure rules: recipe, cart, catalog, toon, render
│   ├── application/           # Use cases + ports.py
│   ├── adapters/              # llm/, web/, pdf/, persistence/, email/
│   ├── api/                   # FastAPI app, routes/, schemas/, deps, settings
│   ├── scripts/               # entrypoint, seed data (invented only)
│   └── tests/
├── ui/
│   ├── package.json, Dockerfile, Dockerfile.dev
│   ├── app/                   # Pages + BFF routes under app/api/
│   └── components/
├── mcp/                       # MCP server (separate container, isolated)
│   ├── pyproject.toml, uv.lock, .python-version (3.12), Dockerfile
│   ├── server/                # MCP server entry point + tools
│   ├── tools/                 # Recipe, cart, conversation tools
│   └── tests/
└── dev/                       # Support material, not part of the app
    ├── docs/                  # prd.md, prd-v0-es.md, course PDFs
    ├── prompts/               # Working notes and prompts from Sebastián
    ├── memory/                # Daily memory files (ddMMYY.md) and history.md
    └── skills/                # Work states and procedures
```

If a file does not exist yet, create it following this structure. Do not add
new folders without asking.

### Spec folders

Each speckit spec lives in `specs/NNN-short-name/`, where `NNN` is the number of
the backlog story it specifies, zero-padded to three digits: S-016 is
`specs/016-capture-recipe-text/`, S-055 is `specs/055-notebooks/`. The one
exception is `specs/001-finance-dashboard-reuse/`, the bootstrap spec, which
covers S-001 to S-014. Create a spec with
`.specify/scripts/bash/create-new-feature.sh --number <story number> --short-name <name> "<description>"`
so the number is the story's and not the next free one. The folder number says
which story a spec is for; it does not say the order to build them in (see
`dev/docs/backlog.yaml`). A spec for a story that has no backlog entry yet needs
that entry added first.

## Development environment

Prerequisites: Docker with Compose v2, `uv`, Node/`npm`.

- First time: `cp .env.example .env`, fill in the values, and create the data
  directory outside the repo:
  `mkdir -p "${MELOS_DATA:-$HOME/melos}/pgdata"`.
- Start the hot-reload stack (`db`, `api`, `ui`, `mcp`):

  ```bash
  ./scripts/compose-up.sh        # foreground
  ./scripts/compose-up.sh -d     # detached
  ./scripts/compose-down.sh      # stop, keep data
  ./scripts/compose-restart.sh -d
  ```

  UI at <http://localhost:3000>, API at <http://localhost:8000>, MCP at <http://localhost:9000>. Health:
  `/health` on both. There is no reverse proxy in development.
- Parallel work in a git worktree: `./scripts/worktree/worktree-add.sh <slug>
  <branch>`, then the bootstrap script it prints (see `scripts/worktree/README.md`).

### Python (api/) — uv only

ALWAYS use `uv`. Never use `pip`, `python -m venv` or `requirements.txt`.

- `cd api && uv sync --group dev`
- Add a library: `uv add <package>` (or `uv add --group dev <package>`).
  Never edit `uv.lock` by hand.
- Run anything with `uv run <command>`.

### Node (ui/)

- `cd ui && npm install`; add a library with `npm install <package>`.
- No deprecated code, including transitive dependencies. If CI or a local run
  prints a deprecation warning, find the dependency chain with
  `npm ls <module>` (for example, `npm ls punycode`) and fix it at the source.
- To replace a transitive dependency, use an `overrides` entry in
  `ui/package.json`, then delete the stale nested copy and its entry in
  `package-lock.json` and run `npm install`. Re-run lint, typecheck and tests.
  Keep the override and say why in the commit message.
- Known case: `eslint@9` → `ajv@6` → `uri-js` loads Node's deprecated built-in
  `punycode` (DEP0040). Fixed by overriding `uri-js` to `npm:fast-uri@4.2.3`
  (`overrides.ajv["uri-js"]`). Installing the `punycode` npm package does not
  help, because Node resolves the bare name to its built-in first. The
  remaining `punycode` copy under `jsdom` → `whatwg-url` → `tr46` does not
  print the warning; check it if the warning comes back.

## How to check that it works

- **api, in Compose (canonical):**
  `docker compose -f docker-compose.yml -f docker-compose.test.yml run --rm --build api`
- **api, on the host:** `cd api && uv run pytest -q` (needs a reachable
  Postgres; see the README) and `uv run ruff check .`
- **ui:** `cd ui && npm test && npm run lint && npm run typecheck`
- **In the browser:** start the stack and walk the acceptance criteria in
  `dev/docs/prd.md` §2. Key cases:
  1. Text with "a pinch of salt" and "2 large onions" → a draft where salt
     has a vague note and onion is `2 unit large`.
  2. Recipe A with 3 tbsp flour + recipe B with 1 cup flour in the cart →
     `flour — 1 cup + 3 tbsp` with chips A and B.
  3. "What's the weather tomorrow?" as a recipe → "That doesn't look like a
     recipe." and nothing is saved.
  4. Asking something the recipes don't cover → the assistant says the
     recipes don't cover it.

## Governance and Rules

**The [Project Constitution](.specify/memory/constitution.md) is the source of truth for engineering principles.** This section highlights key rules; see the constitution for the complete set with rationale and how to apply them.

### Core Rules

- Secrets live only in `.env` (local) or the server's environment
  (production): `GEMINI_API_KEY`, `POSTGRES_PASSWORD`, `SESSION_SECRET`, SMTP
  credentials. Never in code, the README, fixtures or the chat. Do not read or
  display the contents of `.env`.
- `.env`, `.venv/` and `node_modules/` must be in `.gitignore`.
- English for code, documentation and UI. UI text is simple, for someone
  without technical knowledge. Recipe content may be English or Spanish.
- `domain/` imports nothing from `adapters/`, `api/`, FastAPI, SQLAlchemy or
  the Gemini SDK.
- Every external call (Gemini, web fetch, SMTP) goes through a port, and its
  errors map to a clear user message (`dev/docs/prd.md` §1.7). The user's
  input is never lost on error.
- Every kitchen-scoped query checks membership in `application/`. A
  non-member gets `404`.
- Every recipe query checks that the recipe is in a personal notebook the
  caller owns or is a member of, or in a notebook of a kitchen the caller
  belongs to. Otherwise `404`.
- Schema changes go through Alembic migrations.
- Small changes: one per request. When finished, explain what you changed and
  why.
- If you add a library, say so.
- Do not use real personal data. For tests and seeds, invent examples.

## Work states (skills)

The `dev/skills/` folder contains five thinking states of Sebastián. Before
answering, choose the state that matches the intent of the request, read its
file and follow its guidelines. If the intent is unclear, ask which one to use.
If Sebastián names a state (for example, "Creating mode"), use that one.

| Request intent                                                    | State                        | File                           |
| ----------------------------------------------------------------- | ---------------------------- | ------------------------------ |
| Understand emotions, reactions or tension with other people       | 🪞 Reflecting                | `dev/skills/State_Reflecting.md`   |
| Learn or master a new concept                                     | 📚 Learning                  | `dev/skills/State_Learning.md`     |
| Analyze a problem or decision, compare options                    | 🧩 Reasoning / Logic         | `dev/skills/State_Logic.md`        |
| Build something: prototype, script, system, design or text        | 🛠️ Creating                  | `dev/skills/State_Creating.md`     |
| Reduce friction, standardize or automate a process                | ⚙️ Optimizing / Systems      | `dev/skills/State_Optimizing.md`   |

At the start of the answer, state in one line which state you used (for
example, "State: 🧩 Reasoning / Logic").

Other procedures in `dev/skills/`: `save_to_memory.md` (memory), `using_toon.md` (object encoding for LLMs), and `toon_guidelines.md` (reference).

## Memory (dev/memory/)

Every relevant interaction is persisted in `dev/memory/`, using the procedure
in `dev/skills/save_to_memory.md`.

- Relevant means: a decision, a preference or correction from Sebastián, a
  project fact that is not already in the repo, or a finished change. Skip
  greetings, small talk and questions with no lasting outcome.
- Write one short line per fact, in English, with the command from
  `dev/skills/save_to_memory.md`. It appends to today's file,
  `dev/memory/ddMMYY.md`, and creates it if missing. Run it from the repo root.
- Escape single quotes in the content (`'` becomes `'\''`) so the command does
  not break.
- Never save secrets, API keys, `.env` contents or real personal data.
- Append only. Do not edit or delete existing lines without asking.

### Agent behavior with memory

- **Session start:** Read all files in `dev/memory/` to load context from prior
  interactions.
- **After each response:** Review `dev/skills/save_to_memory.md` and consider
  what, if anything, should be saved about this interaction.

## Amendments to Governance

Changes to this document (AGENTS.md) or the [Project Constitution](.specify/memory/constitution.md) require explicit approval and should be documented.

**To amend the constitution:**
```bash
/speckit-constitution
```

This will guide you through updating principles, versioning, and recording changes.

## What not to do

- Do not delete or rewrite the README without asking.
- Do not change the Gemini model, the auth layer or the architecture
  (services, layers, dependencies) without asking.
- Do not add auth features that finance-dashboard doesn't have.
- Do not add reverse proxy, TLS or server configuration; the server is managed
  separately.
- Do not copy finance-dashboard's seed credentials or finance domain code
  (cards, statements, budgets, splits, FX, bank adapters).
- **Do not violate the [Project Constitution](.specify/memory/constitution.md).** If you need an exception, ask for written approval and document it.
- Do not push or deploy without my review first.
- Do not build a second add-recipe entry point or its options on a page. Use
  the shared add-recipe call to action.
