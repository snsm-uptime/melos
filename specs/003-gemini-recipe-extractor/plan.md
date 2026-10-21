# Implementation Plan: Recipe Extraction Assistant Adapter

**Branch**: `s15` (spec folder `003-gemini-recipe-extractor`) | **Date**: 2026-10-20 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/003-gemini-recipe-extractor/spec.md`

## Summary

Build the internal boundary that turns pasted recipe text into one of three
outcomes the capture feature (S-016) can rely on: a checked draft, a
"not a recipe" answer, or one of four failure classes (unavailable,
limit reached, invalid output, `AIProviderError`). The boundary is a port in the application
layer, implemented by a Gemini adapter (`google-genai`, one attempt, timeout
from settings), plus a fake adapter for tests. Recipe rules (units, sizes,
quantities, names, servings, categories) live in a pure domain module and are
enforced before any draft leaves the boundary. Nothing is stored.

The approach follows the hexagonal layout already fixed by the constitution:
`domain/` holds the rules, `application/` holds the port and the use case,
`adapters/llm/` holds the Gemini and fake implementations. No new service, no
route, no migration.

## Technical Context

**Language/Version**: Python 3.12 (`api/.python-version`), managed with `uv`

**Primary Dependencies**: `google-genai` (Gemini SDK, the only LLM SDK allowed), existing FastAPI + pydantic settings in `api/api/settings.py`. `google-genai` is added with `uv add google-genai` and called out in the PR, per AGENTS.md.

**Storage**: N/A. The feature writes nothing (FR-011, SC-007). No Alembic migration.

**Testing**: pytest (`api/tests/`), ruff. Domain tests are pure pytest. Use-case tests use a fake port. One adapter test uses a stubbed SDK client and never touches the network. Full run through `docker compose -f docker-compose.yml -f docker-compose.test.yml run --rm --build api`.

**Target Platform**: Linux container (`api` service in Docker Compose).

**Project Type**: Internal module of the existing `api` web service. No endpoints in this feature.

**Performance Goals**: A timed-out call returns "unavailable" within the configured wait + 1 s (SC-005). Defaults: 10 s for text and URL, 30 s for image.

**Constraints**:
- Pasted text capped at 10,000 characters, refused before any call (spec edge case).
- One attempt per call; no automatic retry (Clarifications, Q4).
- Model names and key come from settings only (FR-009, constitution §2).
- Logs never contain the key, the full pasted text, or a full service response (FR-014).
- Pasted text is delimited as data and the prompt tells the model to ignore instructions inside it (FR-007, constitution §4).

**Scale/Scope**: One household per kitchen, one extraction per user action. Single feature, about 4 new source modules and 4 test modules.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Check | Status |
|-----------|-------|--------|
| §1 Simplicity and Reuse: no new services, auth untouched, external calls through a port | Only the `api` service changes. No queue, no worker. Gemini call goes through a port. Auth layer not touched. | PASS |
| §2 Tech stack: Python 3.12 + uv, Gemini via `google-genai`, model names from env | `google-genai` via `adapters/llm/` only. Model names and timeouts from settings. Adding the library is a `uv add`, not a hand edit of `uv.lock`. | PASS (adds one dependency: `google-genai`, to be stated in the PR) |
| §3 Hexagonal: `domain/` pure; `application/` owns ports; `adapters/` implement them; adapter errors become domain errors | Rules in `domain/recipe_draft.py` with no imports from SDK or FastAPI. Port in `application/recipe_extraction.py`. SDK exceptions caught only in `adapters/llm/gemini_extractor.py` and mapped to the result classes. | PASS |
| §4 Security: secrets in env only; no real data in tests; delimiters around pasted text | Key read from settings and never logged. Test text is invented. Prompt wraps pasted text in delimiters. URL fetching is out of scope here. | PASS |
| §5 No AI shortcuts: no draft saved without confirmation; answers only from the kitchen's data; nothing stored | Feature stores nothing and returns a draft only as a value. The "answer from recipes only" chat rule is not in this feature. | PASS |
| §6 Testing: domain pure pytest; use cases against fake ports; no network | Domain tests have no mocks. Use-case tests use `FakeRecipeExtractor`. Adapter test stubs the SDK client. | PASS |
| §7 Deployment: Compose only; no proxy or TLS | No compose or proxy change. New env vars added to `.env.example` only. | PASS |
| §8 Git discipline: small commits; no `--no-verify`; Alembic for schema | Work is split into small commits (see Phase breakdown below). No schema change. | PASS |
| §9 Scope: must be in v1 Must list | S-015 is the prerequisite of S-016 (capture from text, a Must story). Spec states it is in scope. | PASS |
| AGENTS.md: `adapters/llm/` is the documented home for Gemini | Matches the documented layout. No new top-level folder. | PASS |

**Known tension (resolved)**: categories are a controlled vocabulary
(`categories.yaml`, `cuisine.yml`): at most two main ingredients and two cuisines,
zero allowed, with `international` when no cuisine matches. The spec,
PRD §1.6, §2 J2 and Appendix B.1 are updated to match.

**Result**: No violations. Complexity Tracking is not needed.

## Project Structure

### Documentation (this feature)

```text
specs/003-gemini-recipe-extractor/
├── spec.md                       # Feature spec (input)
├── plan.md                       # This file
├── research.md                   # Phase 0 output
├── data-model.md                 # Phase 1 output
├── quickstart.md                 # Phase 1 output (validation guide)
├── contracts/
│   └── recipe-extraction-port.md # Internal port contract for S-016
└── tasks.md                      # Created by /speckit-tasks, not here
```

### Source Code (repository root)

```text
api/
├── domain/
│   └── recipe_draft.py           # NEW: pure rules (units, sizes, lines, servings, categories)
├── application/
│   └── recipe_extraction.py      # NEW: ExtractionResult types, RecipeExtractor port, use case
├── adapters/
│   └── llm/                      # NEW
│       ├── __init__.py
│       ├── gemini_extractor.py   # NEW: google-genai adapter, error mapping, prompt build
│       ├── prompt.py             # NEW: prompt text with delimiters (kept apart for review)
│       └── fake_extractor.py     # NEW: stand-in returning chosen results (FR-010)
├── api/
│   └── settings.py               # EDIT: GEMINI_API_KEY, GEMINI_CHAT_MODEL, timeouts
├── tests/
│   ├── test_recipe_draft_domain.py          # NEW: rules, per FR-006 and SC-003
│   ├── test_recipe_extraction_application.py # NEW: outcomes, classes, empty/long input, no storage
│   └── test_gemini_extractor_adapter.py     # NEW: stubbed SDK client, error mapping, log hygiene
└── .env.example                  # EDIT: new variables, no real values
```

**Structure Decision**: Extend the existing `api/` layers. Nothing in `ui/`,
`mcp/`, or the database changes. The `adapters/llm/` directory is the one
documented in AGENTS.md, so no new top-level folder is needed.

## Design Decisions (summary; detail in research.md)

1. **Single boundary**: `RecipeExtractor` port with one method
   `extract(text, ingredient_names, timeout_s) -> ExtractionResult`.
   The use case is the only caller. The adapter is the only place that
   catches SDK exceptions.
2. **Result type**: a closed set of frozen dataclasses (`Draft`,
   `NotARecipe`, `Unavailable`, `LimitReached`, `InvalidOutput`). No raw
   exception or text is carried in any failure.
3. **Structured output**: ask Gemini for JSON matching a response schema.
   Parse with pydantic models in the adapter. Any parse failure becomes
   `InvalidOutput`.
4. **Rules after parsing**: the domain module applies the FR-006 rules to the
   parsed draft. A rule break becomes `InvalidOutput`. Unit mapping
   ("tablespoon" → "tbsp"), one-edit typo matching for units of 5 or more characters ("tablespon" → "tbsp"), and size removal (size with non-"unit" unit, or a size outside small, medium, large) are
   applied here, before the rule check, as the spec's edge cases require.
5. **Timeouts and attempts**: per-call timeout chosen by the caller's input
   kind (text/URL 10 s; image 30 s is recorded for S-040 and not used here), passed to the SDK as its per-request
   timeout. The SDK's built-in retry is disabled so there is exactly one
   attempt.
6. **Stand-in**: `FakeRecipeExtractor` takes a scripted result and returns it
   unchanged. It is the only extractor used by the test suite.

## Phase breakdown (for tasks; not tasks.md)

- **P0 Research**: done in `research.md`.
- **P1 Domain**: `recipe_draft.py` and its tests. Pure, no I/O. First commit.
- **P2 Application**: port, result types, use case (length check, empty check,
  classification, rules), tests against the fake. Second commit.
- **P3 Adapter**: settings, prompt, Gemini adapter, error mapping, adapter
  tests with a stubbed client. Third commit. Add `google-genai` via `uv add`.
- **P4 Verify**: full api test run in Compose, `ruff check`, and the manual
  AI evaluation set (SC-002, SC-004) once a real key is available locally.

## Re-check after Phase 1 design

The design keeps every item above. The only new dependency is `google-genai`,
which the constitution already names. Re-check result: **PASS**.
