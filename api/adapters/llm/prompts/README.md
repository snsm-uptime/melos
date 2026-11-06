# Prompt templates

Each file here holds one prompt, and each file has one purpose. The code in
`adapters/llm/prompt.py` fills the placeholders with `render()` from
`adapters/llm/prompt_templates.py`.

| Template | Purpose | Used by | Placeholders |
|---|---|---|---|
| `recipe_extraction_system.md` | System instruction for the recipe extractor: outcomes, recipe fields, matching rules | `system_instruction()` → `GeminiRecipeExtractor` | `TEXT_OPEN`, `TEXT_CLOSE`, `NAMES_OPEN`, `NAMES_CLOSE`, `VAGUE_PHRASES` |
| `recipe_extraction_user.md` | User turn: the pasted text and the catalog names, each in its own delimited block | `build_contents()` → `GeminiRecipeExtractor` | `TEXT_OPEN`, `TEXT`, `TEXT_CLOSE`, `NAMES_OPEN`, `NAMES_JSON`, `NAMES_CLOSE` |
| `recipe_extraction_page_part_system.md` | System instruction for one part of a long web page (spec 026, partial page mode): outcomes `recipe_part`, `no_recipe_content`, `multiple_recipes`, and the same security and line rules as the whole-recipe template | `page_part_system_instruction()` → `GeminiRecipeExtractor` in `ExtractionMode.PAGE_PART` | `TEXT_OPEN`, `TEXT_CLOSE`, `NAMES_OPEN`, `NAMES_CLOSE`, `VAGUE_PHRASES` |
| `recipe_extraction_page_part_line.md` | The line put before the user turn in partial page mode: which part of the page this is | `build_contents(..., part=(i, n))` | `PART`, `TOTAL` |
| `ingredient_pairs_system.md` | System instruction for suggested pairs (spec 043): English and Spanish names of one catalog that are the same ingredient | `pairs_system_instruction()` → `GeminiPairSuggester` | `NAMES_OPEN`, `NAMES_CLOSE` |
| `recipe_language_system.md` | System instruction for the one-time language proposal (spec 043 FR-005a): "en", "es" or "unsure" | `language_system_instruction()` → `GeminiLanguageDetector` | `TEXT_OPEN`, `TEXT_CLOSE` |

The security rule and the recipe field rules are written twice, once in each system template, and
must stay identical: `tests/test_prompt_characterization.py` compares the two blocks. Change both
together.

## Syntax

- A placeholder is `{{NAME}}`, with the name in capitals and underscores.
- Every placeholder in a template must be given a value, and every value must match a placeholder. Otherwise `render()` raises `PromptTemplateError`.
- Values are inserted once. A value that contains `{{…}}` (for example, pasted recipe text) is inserted as text and never expanded again.

## Rules

- One purpose per file. A template holds prompt text only, with no code.
- Changing a template's wording changes what the model is told. Regenerate its golden file in `api/tests/fixtures/prompts/` in the same commit and say why in the commit message.
- Pasted text and catalog names are data, never instructions (constitution §4). Keep the security rule in the system template.

## MVP-OUT: main ingredients (S-061)

A template cannot hold a comment, because the model would read it. The rule below was removed from
`recipe_extraction_system.md` (after `base_servings`) on 2026-10-27. To restore it, paste it back, add
`MAIN_KEYS` to `system_instruction()` and to the placeholder list above, and regenerate the golden file.

```text
- main_ingredients: at most two keys, chosen only from this list: {{MAIN_KEYS}}.
  Choose the ingredient that defines the dish. Use none when no key fits. Aromatics, fats, sauces and spices are never a main ingredient.
```
