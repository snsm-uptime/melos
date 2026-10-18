# Feature Specification: Melos Recipe & Kitchen System

**Feature Branch**: `001-recipe-kitchen-system`

**Created**: 2026-10-18

**Status**: Draft

**Input**: User description: "A meal planning system that turns recipes from any source (free text, web pages, cookbook photos) into structured recipes in a shared kitchen. The system answers questions about recipes and ingredients and builds consolidated shopping lists scaled to the number of people eating."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Add Recipe to Kitchen (Priority: P1)

A non-technical home cook captures a recipe from a source (free-form text, website URL, or photo of a cookbook page) and stores it in their shared kitchen. The recipe is structured automatically into standardized format with ingredients, quantities, and instructions.

**Why this priority**: Core MVP—without the ability to capture recipes, the entire system has no data. This is the entry point for all users.

**Independent Test**: Can be fully tested by user providing a recipe in any format, system extracting ingredients and storing in kitchen, and user viewing the structured recipe. Delivers immediate value: a permanent, searchable copy of the recipe.

**Acceptance Scenarios**:

1. **Given** user has a kitchen and a recipe in free text, **When** they paste the text into the recipe importer, **Then** the system extracts ingredients (with quantities/units) and instructions and saves the recipe to their kitchen.
2. **Given** user has a cookbook or website URL, **When** they provide a link, **Then** the system parses the content and extracts the recipe.
3. **Given** user has a photo of a cookbook page, **When** they upload the image, **Then** the system uses OCR/vision to extract the recipe text and structures it.
4. **Given** the system extracted a recipe, **When** the user views it, **Then** ingredients show quantities, units, and are matched to the kitchen's ingredient catalog (or flagged as new).

---

### User Story 2 - View Kitchen Inventory & Recipes (Priority: P1)

A user views their shared kitchen—all recipes they've added, the complete ingredient catalog, and which ingredients are available or needed.

**Why this priority**: Once recipes are captured, users need visibility into their kitchen. Without this, they can't answer "what can we make this week?" or "what do we need to buy?"

**Independent Test**: Can be fully tested by adding recipes to a kitchen and verifying the UI displays all recipes, ingredients, and their attributes (quantity, unit, kitchen-wide standardization).

**Acceptance Scenarios**:

1. **Given** a kitchen with multiple recipes, **When** the user opens their kitchen view, **Then** they see all recipes with titles, ingredients, and cooking instructions.
2. **Given** recipes with overlapping ingredients (e.g., "2 cups flour" in one, "3 cups flour" in another), **When** the user views the kitchen, **Then** the ingredient catalog shows "flour" as a single entry with all instances listed.
3. **Given** a shared kitchen with Members and Owners, **When** a user views the kitchen, **Then** they see all recipes added by any household member, not just their own.

---

### User Story 3 - Generate Consolidated Shopping List (Priority: P1)

Given a set of recipes selected for the week and a headcount, the user generates a single consolidated shopping list with merged and scaled ingredients.

**Why this priority**: The core user goal—eliminating manual shopping list creation. Without this, the system hasn't solved the original problem.

**Independent Test**: Can be fully tested by selecting recipes, specifying headcount, and verifying the output is a consolidated list with quantities properly scaled and merged by ingredient.

**Acceptance Scenarios**:

1. **Given** two recipes: Recipe A (2 cups flour), Recipe B (3 cups flour), **When** user selects both for a shopping list, **Then** the list shows "5 cups flour" (merged and summed).
2. **Given** a recipe for 4 people and the user has 6 people eating, **When** they generate the shopping list, **Then** all quantities are scaled by 1.5x (e.g., "2 cups flour" becomes "3 cups flour").
3. **Given** a shopping list, **When** the user views it, **Then** ingredients are grouped by category (produce, dairy, pantry, etc.) for easier shopping.
4. **Given** a shopping list, **When** the user requests a PDF, **Then** the system generates a printable document with the formatted list.

---

### User Story 4 - Answer Questions About Kitchen (Priority: P2)

A user asks the system natural-language questions about their kitchen: "Do we have eggs?", "What meals can we make with these 5 ingredients?", "How much flour do our recipes need this week?"

**Why this priority**: Reduces friction for meal planning. Users can quickly query their kitchen without manually reviewing all recipes.

**Independent Test**: Can be fully tested by seeding a kitchen with recipes and ingredients, asking questions, and verifying answers match kitchen state.

**Acceptance Scenarios**:

1. **Given** a kitchen with recipes and ingredient inventory, **When** user asks "what ingredients do we need?", **Then** the system responds with a list of ingredients required across all selected recipes.
2. **Given** a recipe containing eggs and a query "can we make a vegetarian meal?", **When** user asks, **Then** the system correctly identifies meals that can or cannot be made based on ingredients.
3. **Given** conflicting ingredient information (e.g., "we have milk" vs. ingredients call for milk), **When** user asks about ingredient availability, **Then** the system responds with confidence based on the kitchen's shared state.

---

### User Story 5 - Manage Shared Kitchen & Members (Priority: P2)

A kitchen Owner invites household members, sets permissions (who can add/edit recipes), and manages the shared kitchen's ingredient catalog.

**Why this priority**: Enables multi-user households. Necessary for the "couple" use case but not blocking initial recipe capture.

**Independent Test**: Can be fully tested by creating a kitchen, inviting a member, and verifying permissions (who can view, add, edit recipes).

**Acceptance Scenarios**:

1. **Given** a kitchen Owner, **When** they invite a Member by email, **Then** the Member receives an invitation and can join the kitchen.
2. **Given** a Member invited to a kitchen, **When** they try to add a recipe, **Then** the system allows it (Member permission).
3. **Given** a Visitor shared a recipe link, **When** they try to edit the recipe or add ingredients, **Then** the system denies it (Visitor can view only).

---

### User Story 6 - Standardize Ingredient Names Across Kitchen (Priority: P3)

When multiple recipes reference the same ingredient with different names or spellings ("flour" vs. "all-purpose flour" vs. "APF"), the system standardizes them in the kitchen catalog. Users can define canonical names for ingredients.

**Why this priority**: Improves data quality and shopping list accuracy but not blocking MVP. Valuable after initial recipe collection.

**Independent Test**: Can be fully tested by adding recipes with variant ingredient names and verifying they are merged or offered for standardization.

**Acceptance Scenarios**:

1. **Given** recipes with "olive oil," "extra virgin olive oil," and "EVOO," **When** the user reviews the ingredient catalog, **Then** the system suggests merging them under a canonical name.
2. **Given** a user-defined canonical ingredient "butter," **When** a new recipe uses "unsalted butter," **Then** the system prompts to match it to the kitchen's standard.

---

### Edge Cases

- What happens when a user uploads a malformed recipe (missing ingredients or instructions)?
- How does the system handle recipes with variable ingredient quantities (e.g., "salt to taste")?
- What if a recipe cannot be parsed from a web page or image (OCR fails)?
- How does the system handle dietary restrictions or ingredient substitutions (e.g., vegan alternatives)?
- What happens if a Member deletes a recipe that the Owner added?
- How does the system scale recipes with non-linear ingredients (e.g., "a pinch of salt" doesn't scale linearly)?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST accept recipes in multiple formats: free-form text, URLs (website recipes), and images (cookbook pages).
- **FR-002**: System MUST extract ingredients with quantities and units from any recipe source automatically.
- **FR-003**: System MUST extract cooking instructions and metadata (cook time, yield, difficulty) from recipes.
- **FR-004**: System MUST structure recipes into a standardized schema stored in the shared kitchen.
- **FR-005**: System MUST maintain a shared kitchen catalog of ingredients with standardized names.
- **FR-006**: System MUST allow matching ingredient names across recipes to the kitchen's canonical catalog.
- **FR-007**: System MUST generate a consolidated shopping list from selected recipes, merging duplicate ingredients.
- **FR-008**: System MUST scale recipe ingredient quantities based on the number of people eating.
- **FR-009**: System MUST answer natural-language questions about kitchen state (available ingredients, recipes, meal suggestions).
- **FR-010**: System MUST support role-based access: Visitors (view only), Members (add/edit recipes), Owners (manage kitchen and members).
- **FR-011**: System MUST allow Owners to invite Members to the kitchen via email or unique invite link.
- **FR-012**: System MUST persist all recipes, ingredients, and kitchen data durably.
- **FR-013**: System MUST generate printable PDFs of shopping lists.
- **FR-014**: System MUST support multiple households (kitchens) with separate data.
- **FR-015**: System MUST log all changes to recipes and kitchen state for auditability.

### Key Entities

- **Kitchen**: Represents a household's shared space. Contains recipes, ingredient catalog, and member roster. Owned by one user; members can be invited. Attributes: name, members, ingredient catalog, recipes, created_at, last_modified.
- **Recipe**: A single meal or dish with ingredients and instructions. Belongs to one kitchen. Attributes: title, ingredients (with quantities), instructions, source (URL or uploaded), cook_time, yield, difficulty, created_by, created_at.
- **Ingredient**: An ingredient in the kitchen's catalog with a standardized name. Maps to multiple recipe ingredients with the same semantic meaning. Attributes: canonical_name, aliases, category, unit, last_updated.
- **RecipeIngredient**: A link between a Recipe and Ingredient with specific quantity and unit. Attributes: recipe_id, ingredient_id, quantity, unit, notes.
- **ShoppingList**: A consolidated list generated from selected recipes and headcount. Attributes: kitchen_id, recipes_selected, headcount, ingredients (with scaled quantities), generated_at, generated_by.
- **Member**: A user with access to a kitchen. Has a role (Visitor, Member, Owner). Attributes: user_id, kitchen_id, role, invited_at, joined_at.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can add a recipe (from any source: text, URL, or image) in under 2 minutes.
- **SC-002**: System successfully extracts ingredients and quantities from 95% of recipes (measured across test suite of diverse recipes).
- **SC-003**: Users can generate a shopping list from 5+ recipes and see a consolidated, merged list in under 10 seconds.
- **SC-004**: Ingredient scaling is accurate to within 5% of manual calculations for common household quantities (cups, tablespoons, etc.).
- **SC-005**: Kitchen Assistant answers questions about available ingredients or meal suggestions with 90%+ accuracy based on kitchen state.
- **SC-006**: System supports at least 10 concurrent users in a single kitchen without performance degradation.
- **SC-007**: 90% of non-technical users (target demographic) complete basic workflows (add recipe, view kitchen, generate list) without help.
- **SC-008**: System handles recipes with 50+ ingredients and kitchens with 100+ recipes without slowdown.
- **SC-009**: Ingredient standardization reduces duplicate ingredient names by 80% compared to raw input.
- **SC-010**: Users report that the system saves them at least 30 minutes per week on meal planning and shopping list creation.

## Assumptions

- **User Technical Literacy**: Users are non-technical home cooks. UI/UX must require minimal instruction; error messages must be plain English.
- **Recipe Sources**: Recipes come from cookbooks, food websites, or handwritten notes. System assumes input may be messy or incomplete and handles gracefully.
- **Ingredient Quantities**: Most recipes use standard US measurements (cups, tablespoons, teaspoons, ounces, pounds). Metric conversion is out of scope for v1.
- **Scaling Linearity**: Ingredient quantities scale linearly with headcount (e.g., doubling the headcount doubles all ingredient quantities). Non-linear ingredients (e.g., "a pinch of salt") are handled by user review.
- **Kitchen Ownership**: Each kitchen has one Owner (the person who set it up); households are assumed to be small (2-6 people).
- **Data Persistence**: Recipes and kitchen data are the user's most valuable asset. System assumes reliable, persistent storage; data loss is unacceptable.
- **AI Integration Scope**: Recipe extraction and question answering use AI. Ingredient substitution, meal recommendations based on preferences, and dietary filtering are out of scope for v1.
- **Authentication**: Reuses existing authentication system (assumed available). Users log in via email/password or OAuth.
- **PDF Generation**: Shopping lists are generated as downloadable PDFs; email delivery is out of scope for v1.
- **Invite Workflow**: Kitchen invitations use unique links or email-based flows (exact mechanism TBD based on existing auth system).
- **Mobile Support**: v1 targets desktop web; mobile app is out of scope (May investigate responsive design for phones in v2).
