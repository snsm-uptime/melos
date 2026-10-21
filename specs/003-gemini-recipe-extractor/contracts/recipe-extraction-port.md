# Contract: Recipe extraction port (internal)

This feature exposes no HTTP endpoint. Its contract is the Python port that
S-016 (capture from text) calls. The shape of the result types is in
[data-model.md](../data-model.md).

Normative status: this contract is normative for field names and shape. `spec.md` is normative for behaviour. A conflict is fixed in the spec first.

## Port

Location: `api/application/recipe_extraction.py`

```text
RecipeExtractor.extract(
    text: str,
    ingredient_names: list[str],
    timeout_s: float,
) -> ExtractionResult
```

- Returns exactly one of `Draft`, `NotARecipe`, `Unavailable`, `LimitReached`,
  `InvalidOutput`, `AIProviderError`.
- Never raises for service, network, or output problems. Those are results.
- Raises a domain error only for input refused before any call: empty or
  whitespace-only text, and text over 10,000 characters. These are not service
  failures and do not count against the service.
- Stores nothing and changes no kitchen, recipe, ingredient, category or step.

## Implementations

| Implementation | Location | Use |
|----------------|----------|-----|
| `GeminiRecipeExtractor` | `api/adapters/llm/gemini_extractor.py` | Production. Uses `google-genai`, the model name and key from settings. |
| `FakeRecipeExtractor` | `api/adapters/llm/fake_extractor.py` | Tests and S-016 development. Returns scripted results, no network. |

## Caller rules (for S-016)

- Pass the timeout for the input kind: 10 s for text. The image value (30 s) is recorded for S-040 and is not used in this feature.
- Do not retry automatically. On `Unavailable` or `LimitReached`, keep the
  member's text and show the message for that class.
- On `InvalidOutput`, show the "could not read that recipe" message. Keep the
  text.
- On `NotARecipe` with reason "Only one recipe at a time", show "Upload only one recipe at a time". Show any other reason as returned. This is not an error state.
- On `AIProviderError`, the assistant is not set up for this deployment. Show a generic "Assistant misconfigured" message and keep the text. Show no detail, because the member cannot fix it. *(Draft: needs approval.)*
- Never display any field that is not in the result type.

## Settings used by the adapter

| Variable | Purpose | Default |
|----------|---------|---------|
| `GEMINI_API_KEY` | Service key. Secret. Empty means every call returns `AIProviderError`. | none |
| `GEMINI_CHAT_MODEL` | Model name. | from `.env.example` |
| `GEMINI_TEXT_TIMEOUT_S` | Wait for text and URL input. | 10 |
| `GEMINI_IMAGE_TIMEOUT_S` | Wait for image input (recorded for S-040; not used in this feature). | 30 |
