# AGENTS.md · Melos

## What this project is

[One sentence: what problem it solves and for whom. Example: "An assistant that
answers the questions of the residents of association X based on its bylaws".]

## How it is built

- Python 3.12, managed with [uv](https://docs.astral.sh/uv/).
- Interface: Streamlit.
- AI: Gemini API with the `google-genai` SDK. The model is in the `MODELO`
  constant in `src/app.py`.
- The full specification is in `dev/docs/prd.md`.

## Project structure

```text
.
├── AGENTS.md          # Instructions for agents (this file)
├── CLAUDE.md          # Redirects to AGENTS.md
├── GEMINI.md          # Redirects to AGENTS.md
├── README.md          # Guide for end users
├── Dockerfile         # Container build for deployment
├── .dockerignore      # Files left out of the container image
├── .gitignore         # Files left out of git (.env, .venv, ...)
├── pyproject.toml     # Metadata and dependencies (managed by uv)
├── uv.lock            # Exact versions; committed to the repository
├── .python-version    # Python version used by uv (3.12)
├── dev/               # Support material for the work, not part of the app
│   ├── docs/
│   │   ├── prd.md     # Product specification
│   │   └── *.pdf      # Course brief, rubric, guidelines and templates
│   ├── memory/        # Daily memory files (ddMMYY.md) and history.md
│   └── skills/        # Work states based on intent (see "Work states" section)
└── src/
    ├── app.py         # The whole Streamlit app
    └── .env           # Local GEMINI_API_KEY; NEVER committed to git
```

Everything that is not the app lives in `dev/`. The app itself lives in `src/`.

If a file does not exist yet, create it following this structure. Do not add
new folders without asking.

## Development environment (uv)

ALWAYS use `uv` for Python and dependencies. Do not use `pip`, `pip install`,
`python -m venv` or `requirements.txt` for local work.

- Prepare the environment (creates `.venv` and installs what `uv.lock` says):

  ```bash
  uv sync
  ```

- Add a library: `uv add <package>` (updates `pyproject.toml` and `uv.lock`).
  To remove it: `uv remove <package>`. Never edit `uv.lock` by hand.
- Run any Python command inside the environment: `uv run <command>`
  (do not activate `.venv` by hand).
- Start the app in development, loading the key from `src/.env`:

  ```bash
  uv run --env-file src/.env streamlit run src/app.py
  ```

  The app runs at <http://localhost:8501> and reloads when changes are saved.

## Rules

- The API key ALWAYS goes in secrets: the `GEMINI_API_KEY` environment
  variable (locally, inside `src/.env`; in deployment, in the platform's
  secrets). Never in the code, the README or the chat. Do not read or display
  the contents of `src/.env`.
- `src/.env` and `.venv/` must be in `.gitignore`.
- Every API call goes inside a `try/except` and shows a clear message to the
  user.
- UI text is in English, simple, written for someone without technical
  knowledge.
- Small changes: one per request. When finished, explain what you changed and
  why.
- If you add a library, do it with `uv add` and say so.
- Do not use real personal data. For testing, invent examples.

## How to check that it works

- Start the app with the development command above and test it in the browser.
- Test cases (input → expected result):
  1. [input] → [expected response]
  2. [input] → [expected response]
  3. [off-topic input] → [the app kindly says it cannot help with that]

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
- Never save secrets, API keys, `src/.env` contents or real personal data.
- Append only. Do not edit or delete existing lines without asking.

## What not to do

- Do not delete or rewrite the README without asking.
- Do not change the model or the architecture without asking.
- Do not push or deploy without my review first.
