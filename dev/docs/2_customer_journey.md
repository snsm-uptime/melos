# 2. Customer journey

> See main PRD at [prd.md](prd.md)

Each stage lists what the user does, the rules, the edge cases and the acceptance criteria (AC).

### J0 · Account
The user signs up, signs in, signs out, resets their password by email and edits their profile. Behaviour is in [1. Architecture](1_architecture.md#13-authentication-layer-reused).

- **AC0.1** Signing up with a 7-character password shows "Password must be at least 8 characters." and creates no account.
- **AC0.2** A wrong password and an unknown email give the same sign-in error.
- **AC0.3** A reset link works once and expires after 1 hour.
- **AC0.4** Repeated failed sign-ins from one IP get `429` with `Retry-After`.

### J1 · Kitchen and members
- Every user gets "My kitchen" on sign up. They can create more, rename them and choose `content_language` (default `en`).
- The owner invites by email. The invitee signs up or signs in and lands in that kitchen.
- A kitchen switcher in the app shell remembers the last kitchen opened.
- **Edge cases:**
  - The last owner cannot leave or be demoted.
  - Changing `content_language` after recipes exist shows a warning: existing names are not translated.
- **AC1.1** A member of kitchen A gets `404` for any resource of kitchen B.
- **AC1.2** An invitee who signs up through the link sees the inviting kitchen first.

### J2 · Capture a recipe
- **Input**, one of three tabs:
  - **Text:** a free description.
  - **URL:** a link to one recipe page.
  - **Photo:** one image of a cookbook page (JPEG/PNG/HEIC, up to 10 MB).
- **Output:** a **draft review screen**:
  - Title, base servings (with an "estimated" badge when Gemini guessed), categories as chips, and the ingredient table and steps, all editable.
  - Each ingredient shows either "matched: *onion*" or "new ingredient", and the user can change the match.
- **Save** creates the recipe and the confirmed new catalog entries, then embeds the recipe. **Discard** saves nothing.
- **Extraction rules** (prompt in [Appendix B](appendix_b_prompts.md)):
  - Canonical names in the kitchen's language: singular, lower-case, preparation in its own field.
  - Vague amounts ("to taste", "a pinch") → `vague_note`.
  - "2 large onions" → `quantity 2, unit unit, size large`.
  - Units are mapped to the allowed set without converting ("tablespoon" → `tbsp`).
  - Servings are taken from the text, or estimated and flagged.
  - 3–5 categories, preferring existing ones.
- **Edge cases:**
  - The input is not a recipe → `NotARecipe`.
  - Two or more recipes in one input → `NotARecipe` with reason "one recipe at a time".
  - The URL has no recipe → `PageFetchFailed`.
  - The page has JSON-LD but no ingredients → fall back to the page text.
  - An empty input disables the button.
- **AC2.1** Text containing "a pinch of salt" and "2 large onions" gives a draft with 3–5 categories: salt has `vague_note`, onion is `2 unit large`.
- **AC2.2** If "onion" is already in the catalog, a new recipe that mentions "onions" matches it instead of proposing a new ingredient.
- **AC2.3** A URL to a page with schema.org Recipe JSON-LD gives a draft whose title and steps come from the JSON-LD.
- **AC2.4** "What's the weather tomorrow?" shows "That doesn't look like a recipe." and saves nothing.
- **AC2.5** If Gemini fails, the typed text is still in the box.

### J3 · Browse and manage recipes
- **List:** cards with title, ingredient count and category chips. Filter by text (title or ingredient) and by category. Each card has a checkbox, "Add to cart".
- **Detail:** ingredients, steps, source link, **Edit**, **Delete** (with confirmation) and **Download PDF**.
- Editing re-embeds the recipe. Deleting removes it from the cart and from vector search; past conversation citations show "deleted recipe".
- **Catalog management** (*Should*): a page listing ingredients and categories with rename and **merge** ("red pepper" → "pepper"). Deleting an ingredient that is still used is blocked; merge it instead.
- **AC3.1** The recipe PDF shows á, é, ñ, ¿, ½ and ⅓ correctly.
- **AC3.2** After deleting a recipe, it doesn't appear in the list, the cart or chat results.

### J4 · Plan (cart)
- Selected recipes go to the kitchen's cart, which members share.
- **Controls:**
  - One global **People** number (default 2).
  - Per recipe, **Meals**: how many times you'll eat it (default 1).
- **Scale factor per recipe:** `people × meals / base_servings`.
- **Edge cases:**
  - An empty cart disables export and shows a hint to add recipes.
  - A recipe deleted while in the cart disappears from it.

### J5 · Shop (shopping list)
**Consolidation (`domain/cart.py`, pure):**
1. Scale each line by its recipe's factor.
2. Group by `(ingredient, dimension)`; preparation is ignored.
3. The same ingredient in different dimensions gives **separate lines**.
4. **Count:** one line per `size` (no size is its own line). Sum first, then round **up** (`ceil`).
5. **Mass and volume:** sum per unit without converting. Join the units from largest to smallest using the order in [1. Architecture](1_architecture.md#16-data-model), e.g. `flour — 1 cup + 3 tbsp`. At most 2 decimals, trailing zeros removed.
6. Lines with `vague_note` go in a separate section, **"Your call"**, de-duplicated by ingredient and listing their notes. An ingredient that is vague in one recipe and measured in another appears in both places.
7. Each line shows **chips** with the titles of the recipes it comes from.

**Export:**
- **PDF**, with the chips as text in parentheses.
- **Markdown** in a copy box, to paste into a chat.

- **AC5.1** Recipe A needs 3 tbsp of flour and recipe B needs 1 cup → `flour — 1 cup + 3 tbsp` with chips A and B.
- **AC5.2** `base_servings=4`, 3 people, 1 meal, 2 eggs → 1.5 is shown as **2 eggs**.
- **AC5.3** Rice in `g` in one recipe and in `cup` in another → two lines.
- **AC5.4** Two recipes with 1 large onion each and one with 1 small onion → `onion, large — 2` and `onion, small — 1`.
- **AC5.5** If PDF generation fails, an error is shown and the Markdown copy still works.

### J6 · Ask (conversations)
- A conversation list (active / archived) and a chat view. **New**, **Rename**, **Archive**, **Unarchive**, **Delete** (with confirmation).
- Typing `@` in the input suggests recipes; a chosen recipe is always included in the context.
- Answers show **cited recipes as links**. When `found=false`, the answer says the kitchen's recipes don't cover it.
- **Sources:** only the kitchen's recipes, ingredients and categories, plus the conversation so far. No web, no general knowledge.
- The first user message sets the default title (first 60 characters).
- **Edge cases:**
  - A kitchen with no recipes disables the input with a hint and makes no API call.
  - A long conversation sends only the last 6 messages.
  - Archived conversations are read-only until unarchived.
- **AC6.1** "Can I swap butter for oil?" with no recipe mentioning it → `found=false` and an answer that the recipes don't cover it.
- **AC6.2** "How many eggs for the tortilla for 6?" scales from the recipe's base servings and cites it.
- **AC6.3** A conversation of user X is invisible to user Y in the same kitchen.
- **AC6.4** A recipe page containing "ignore previous instructions" doesn't change the assistant's behaviour.
