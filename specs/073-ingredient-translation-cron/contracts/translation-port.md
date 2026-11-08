# Contract: Ingredient translation port

Defined in `api/application/ports.py` as `IngredientTranslator`. The Gemini adapter lives in
`api/adapters/llm/gemini_translator.py`. A fake in `api/tests/` is used by application tests.

## Input

```text
IngredientTranslationRequest
  name: str                  # the standard ingredient's name, as discovered (trimmed)
  source_language: "en" | "es"   # the language of the recipe it came from
  target_language: "en" | "es"   # the other supported language
```

Only the name and the two language codes are sent. Recipe text, author, notebook and any personal
data are never sent (constitution 4).

## Output

```text
IngredientTranslationResult
  valid: bool                # false if the text is not an ingredient name
  translation: str | None    # required when valid is true; null when valid is false
```

Rules:
- `valid = true` requires a non-empty `translation`, trimmed, at most 80 characters, with no
  newline.
- `valid = false` means the model judged the text not to be an ingredient name. Nothing is saved,
  and `ai_checked_at` is set (R3).
- Any other shape (missing field, wrong type, extra text around the JSON, empty translation with
  `valid = true`) is a failure, not a result. It raises a domain error. `ai_checked_at` stays null
  and the next run retries (FR-006).

## Prompt

The request is wrapped in a delimited block. The instructions say to treat the block as data, to
ignore any instructions inside it, and to answer only with the JSON shape above (constitution 4,
prompt-injection rule). The prompt text lives in a file next to the adapter, and the model name
comes from `GEMINI_TRANSLATE_MODEL` (FR-015).

## Errors

Adapter errors are mapped to domain errors, never raised raw (constitution 3):

| Adapter condition | Domain error | Effect on the run |
|-------------------|--------------|-------------------|
| Timeout or network error | `TranslationUnavailable` | Counted in `failed`; ingredient retried next run |
| Quota or rate limit | `TranslationUnavailable` | Counted in `failed`; the run stops early to avoid more calls |
| Output not matching the shape | `TranslationUnparseable` | Counted in `failed`; retried next run |
| Model says invalid | none (a normal result) | Counted in `rejected`; not retried |
