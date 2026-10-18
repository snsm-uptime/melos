# 4. Disclaimers (things to avoid)

> See main PRD at [prd.md](prd.md)

**Product**
- The assistant never answers from outside the kitchen's data. No web search, no general cooking, nutrition, allergy or health advice. It never says a recipe is safe for an allergy.
- No crawling. A URL import fetches exactly the one page the user gave.
- Imported recipes are private to the kitchen and keep their source link. No public sharing.
- Photos are not stored; only the extracted text is kept.
- No conversion between units or between mass and volume. No carry-over ("1 cup + 20 tbsp" stays as is).
- An AI draft is never saved without the user confirming it.
- Messages are never edited after they are sent.

**Data and secrets**
- No API keys, passwords or `.env` contents in code, the repo, the README or the chat. `GEMINI_API_KEY` lives only in `.env` / server secrets.
- No real personal data. Fixtures, seeds and examples are invented.
- Don't copy finance's `.env.example` seed credentials.

**For the coding agent**
- Don't change the authentication layer, the Gemini model or the architecture (services, layers, dependencies) without asking. Don't add auth features finance doesn't have (e.g. a signed-in password change form).
- Don't add a reverse proxy, TLS or server configuration to this repo.
- Don't add services, folders or libraries without asking. Add libraries with `uv add` / `npm install` and say so.
- `domain/` imports nothing from `adapters/`, `api/`, FastAPI, SQLAlchemy or the Gemini SDK.
- Every external call (Gemini, web fetch, SMTP) goes through a port and maps errors as in [1. Architecture](1_architecture.md#17-ai-integration-errors-and-safety).
- Don't push or deploy without review.
