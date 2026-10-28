# Research: Match Captured Ingredient Names to the Notebook's Catalog

Resolves the design questions for [plan.md](./plan.md). No NEEDS CLARIFICATION markers remain.

## 1. Where the match is decided

- **Decision**: The rule runs in `check_draft` (domain), after the existing per-line checks, and returns each line's match and the change list.
- **Rationale**: `check_draft` already receives the catalog and already rewrites names against it (`_normalized_name`). Keeping the decision there means the draft response and any later save use one result.
- **Alternatives considered**: A separate application step (more files, same logic, two places to keep in step); the ui computing matches (breaks the rule that the server's draft is the source of truth and would duplicate the rule that S-048 and S-057 need).

## 2. How the model's proposal reaches the rule

- **Decision**: Two new per-line fields in the extraction schema: `text_name` (the ingredient's name as written in the pasted text) and `catalog_match` (the catalog entry the model proposes, or null). Both are optional in the schema.
- **Rationale**: Spec FR-010 needs the text's name for the change list; the assistant's `name` is already normalized. Spec 2026-10-26 Q2 says the model proposes and the rule confirms. The prompt already asks the model to "spell a matching ingredient the same way", so `catalog_match` is the same behaviour made explicit.
- **Alternatives considered**: Asking the model for matches only (no rule: rejected by clarification Q2); deriving `text_name` from the pasted text by the app (fragile: the rule would have to find each name in free text).

## 3. The confirm-or-reject rule

- **Decision**: A line is matched to catalog entry `E` only when `E` is the proposal, and `normalize(text_name)` equals `normalize(E)` under FR-002. Otherwise the line is "new ingredient". A line with no proposal is "new ingredient". Ties (two catalog entries normalize to the same form) are resolved in favour of the entry that equals the proposal exactly; if none does, the line is "new ingredient" (spec FR-008).
- **Rationale**: This is the literal clarification: the model proposes and the rule confirms or rejects each proposal. It keeps the result the same for the same text, catalog and proposal.
- **Alternatives considered**: The rule also matches lines without a proposal (B in Q2 was the model-proposes option; a rule-only match would contradict the chosen answer). Cost: a model that omits a proposal loses the match. That risk is measured by SC-004 in section 6.

## 4. Normalization and singular rules

- **Decision**: `normalize_name` does: trim, Unicode NFKD with combining marks removed (accent-insensitive), casefold, collapse runs of spaces. `singular_forms(name)` returns the name and its singular candidates from fixed rules; a text name and a catalog entry match when their normalized forms, or one text candidate and the catalog form, are equal. English rules: "-ies" → "-y" (berries → berry), "-oes" → "-o" (tomatoes → tomato), "-ves" → "-f" for a short list only (leaves → leaf), "-s" removed when not "-ss"/"-us"/"-is" (onions → onion). Spanish rules: "-es" removed after a consonant (limones → limon, comparing without accents), "-s" removed after a vowel (cebollas → cebolla).
- **Rationale**: Spec 2026-10-26 Q1 requires English and Spanish. Accent-insensitive comparison avoids a miss on "limón"/"limon". A short fixed list avoids guessing irregular forms (spec Assumptions: those become "new ingredient").
- **Alternatives considered**: An NLP lemmatizer (new library: violates constitution §2 without approval); a full plural dictionary (too large for one household's catalogs).

## 5. What the draft shows and what the browser keeps

- **Decision**: The draft response gives each line `match` (`{"kind": "matched", "entry": "onion"}` or `{"kind": "new"}`) and the top-level `changes` list (`{"line": index, "from": "onions", "to": "onion"}`). A matched line's displayed name is the catalog entry; `name` (the assistant's name) is kept so undo can restore it. The browser holds the member's undo and match choices in `captureStore`, and sends nothing back in this feature.
- **Rationale**: Spec FR-013: matches live only in the draft. Spec 016: the draft is not sent back to the api. A change list computed by the server is the same for every client.
- **Alternatives considered**: Sending the member's choices back on save (belongs to S-020).

## 6. Measuring SC-004 (90%)

- **Decision**: Add plural, letter-case and spacing fixtures to `api/tests/fixtures/ai_eval/` (one recipe text per case, with the expected catalog entry). The manual AI evaluation counts how many lines end on the expected entry without a member change. The domain tests cover the rule with the same variants.
- **Rationale**: Constitution §6: AI evaluation is manual on fixtures. Domain tests make the rule's share testable without the model.
- **Alternatives considered**: Automated model evaluation in CI (needs the quota and a real key; out of scope for this story).

## 7. Migration

- **Decision**: No migration.
- **Rationale**: The catalog table and its read path exist (spec 056). Matching adds no stored data (FR-013).
