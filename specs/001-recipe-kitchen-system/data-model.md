# Data Model: Melos Recipe & Kitchen System

**Phase**: 1 (Design)  
**Date**: 2026-10-18  
**Status**: Draft

---

## Overview

This document defines the data entities, relationships, and validation rules for the Melos platform. All entities are kitchen-scoped (every table except auth tables has `kitchen_id`).

## Core Entities

### 1. Kitchen

Represents a household's shared cooking space.

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| `id` | UUID | PK | |
| `name` | String(100) | NOT NULL, Unique per owner | e.g., "My Kitchen", "Family Cooking" |
| `owner_id` | UUID | FK users.id, NOT NULL | Single owner; members invited by owner |
| `created_at` | DateTime | NOT NULL | |
| `updated_at` | DateTime | NOT NULL | |
| `content_language` | Enum | NOT NULL, default='en' | 'en' or 'es' — language for recipe content |
| `timezone` | String(50) | default='UTC' | For scheduling, displays (v2) |

**Relationships**:
- 1 Kitchen : N Recipes
- 1 Kitchen : N Members (via Membership)
- 1 Kitchen : N Ingredients
- 1 Kitchen : N Categories
- 1 Kitchen : N ShoppingLists
- 1 Kitchen : N Conversations

**Validation**:
- Name is non-empty and ≤100 characters
- Owner must be a User
- Cannot delete a kitchen with recipes (cascade not allowed; manual cleanup required)

**State Machine**:
- Created → Active (implicit)
- Active → Archived (out of scope for v1; future feature for deleted kitchens)

---

### 2. Recipe

A single meal with ingredients, instructions, and metadata.

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| `id` | UUID | PK | |
| `kitchen_id` | UUID | FK kitchens.id, NOT NULL | Kitchen this recipe belongs to |
| `title` | String(200) | NOT NULL | e.g., "Chocolate Chip Cookies" |
| `instructions` | Text | NOT NULL | Cooking steps (plain text or markdown) |
| `source_id` | UUID | FK sources.id | Where recipe came from (URL, photo, etc.) |
| `yield_servings` | Integer | default=1 | Base serving count for scaling |
| `cook_time_minutes` | Integer | Optional | e.g., 30 |
| `prep_time_minutes` | Integer | Optional | e.g., 15 |
| `difficulty` | Enum | default='medium' | 'easy', 'medium', 'hard' |
| `created_at` | DateTime | NOT NULL | |
| `updated_at` | DateTime | NOT NULL | |
| `created_by_user_id` | UUID | FK users.id | Author of recipe |

**Relationships**:
- N Recipes : M Ingredients (via RecipeIngredient)
- 1 Recipe : N RecipeIngredients
- 1 Recipe : 1 Source (optional)
- N Recipes : 1 Kitchen
- N Recipes : N Conversations (via Message citations)

**Validation**:
- Title is non-empty, ≤200 characters
- Yield servings ≥ 1
- Cook time, prep time ≥ 0
- Must have at least 1 RecipeIngredient (ingredient lines)
- Must have at least 1 instruction step

**Computed Fields**:
- `total_time_minutes` = cook_time + prep_time
- `embedding` → pgvector (computed when saved/updated)

---

### 3. Ingredient

A standardized ingredient in the kitchen's catalog.

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| `id` | UUID | PK | |
| `kitchen_id` | UUID | FK kitchens.id, NOT NULL | Kitchen's ingredient catalog |
| `canonical_name` | String(100) | NOT NULL, Unique per kitchen | e.g., "Flour - All Purpose" |
| `category_id` | UUID | FK categories.id | e.g., "Pantry", "Produce", "Dairy" |
| `aliases` | Text Array | Optional | Alternative names: ["flour", "APF", "all-purpose"] |
| `unit` | String(20) | default='unit' | Default unit: 'cup', 'tbsp', 'oz', 'lb', 'unit', etc. |
| `created_at` | DateTime | NOT NULL | |
| `updated_at` | DateTime | NOT NULL | |

**Relationships**:
- N Ingredients : 1 Category
- N Ingredients : N Recipes (via RecipeIngredient)
- 1 Kitchen : N Ingredients

**Validation**:
- Canonical name is non-empty, ≤100 characters
- Canonical names are unique per kitchen (case-insensitive)
- Unit must be from allowed list: Cup, Tbsp, Tsp, Oz, Lb, Ml, L, G, Kg, Unit
- Category must exist in this kitchen

**Computed Fields**:
- None

---

### 4. RecipeIngredient

The join table between Recipe and Ingredient, with quantity.

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| `id` | UUID | PK | |
| `recipe_id` | UUID | FK recipes.id, NOT NULL | |
| `ingredient_id` | UUID | FK ingredients.id, NOT NULL | Matched to kitchen catalog |
| `quantity` | Decimal(10,2) | NOT NULL | e.g., 2.5 |
| `unit` | String(20) | NOT NULL | e.g., 'cup', 'tbsp', 'oz' |
| `notes` | String(200) | Optional | e.g., "(to taste)", "(melted)", "(chopped)" |
| `is_linear` | Boolean | default=True | If false, user must review when scaling (e.g., "a pinch") |
| `created_at` | DateTime | NOT NULL | |

**Relationships**:
- N RecipeIngredients : 1 Recipe
- N RecipeIngredients : 1 Ingredient

**Validation**:
- Quantity > 0 (except for items marked as non-linear, then can be 0)
- Unit must match kitchen's allowed units
- If is_linear=False, UI flags for user review during scaling

**Computed Fields**:
- None (scaling happens in domain/cart.py, not in schema)

---

### 5. Category

Groups ingredients in the kitchen (e.g., Produce, Dairy, Pantry).

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| `id` | UUID | PK | |
| `kitchen_id` | UUID | FK kitchens.id, NOT NULL | Kitchen's category list |
| `name` | String(50) | NOT NULL, Unique per kitchen | e.g., "Produce", "Dairy", "Pantry" |
| `sort_order` | Integer | default=0 | For ordering in UI |
| `created_at` | DateTime | NOT NULL | |

**Relationships**:
- 1 Category : N Ingredients

**Validation**:
- Name is non-empty, ≤50 characters
- Names are unique per kitchen

---

### 6. ShoppingList

A consolidated, scaled list generated from selected recipes and headcount.

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| `id` | UUID | PK | |
| `kitchen_id` | UUID | FK kitchens.id, NOT NULL | |
| `recipe_ids` | UUID Array | NOT NULL | Recipes selected for the week |
| `headcount` | Integer | NOT NULL, ≥1 | Number of people eating |
| `generated_at` | DateTime | NOT NULL | Timestamp when list was generated |
| `generated_by_user_id` | UUID | FK users.id | User who created the list |
| `expires_at` | DateTime | Optional | Future: when to re-shop (v2 feature) |

**Relationships**:
- N ShoppingLists : 1 Kitchen
- N ShoppingListItems : 1 ShoppingList (if persisted)

**Validation**:
- recipe_ids must be non-empty, must all exist in this kitchen
- headcount ≥ 1
- Generated timestamp is in the past

**Computed Fields**:
- `items` → derived on-the-fly by domain/cart.py (not stored):
  - For each recipe, get RecipeIngredients
  - Scale quantities by (headcount / recipe.yield_servings)
  - Merge by ingredient_id, summing quantities
  - Return sorted by category, then ingredient name

**Note**: Shopping lists are derived, not persisted. Every read re-computes from recipes. This ensures consistency if recipes change.

---

### 7. Source

Metadata about where a recipe came from.

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| `id` | UUID | PK | |
| `kitchen_id` | UUID | FK kitchens.id | |
| `type` | Enum | NOT NULL | 'url', 'photo', 'text' |
| `url` | String(2048) | Optional (if type='url') | Original URL |
| `photo_filename` | String(255) | Optional (if type='photo') | Stored photo name (not the image itself) |
| `original_text` | Text | Optional (if type='text') | Original pasted text (for audit trail) |
| `created_at` | DateTime | NOT NULL | |

**Relationships**:
- 1 Source : N Recipes (optional one-to-many)

**Validation**:
- If type='url', url must be valid HTTP(S) URL and not private IP
- If type='photo', photo_filename must not be empty
- If type='text', original_text must not be empty

---

### 8. Membership

A user's role and access level in a kitchen (join table between Kitchen and User).

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| `id` | UUID | PK | |
| `kitchen_id` | UUID | FK kitchens.id, NOT NULL | |
| `user_id` | UUID | FK users.id, NOT NULL | |
| `role` | Enum | NOT NULL | 'visitor', 'member', 'owner' |
| `invited_by_user_id` | UUID | FK users.id | Who sent the invite |
| `invited_at` | DateTime | NOT NULL | |
| `joined_at` | DateTime | Optional | When user accepted the invite |
| `is_active` | Boolean | default=True | Soft delete for removed memberships |

**Relationships**:
- N Memberships : 1 Kitchen
- N Memberships : 1 User
- N Kitchens : N Users (via Membership)

**Validation**:
- (kitchen_id, user_id) is unique
- Role must be 'visitor', 'member', or 'owner'
- joined_at is null until user accepts invite (accepts via email link)
- Only 1 owner per kitchen
- A member can only EXIT (leave) a kitchen, not delete it; only the owner can delete a kitchen

---

### 9. Invite

Single-use token for inviting users to a kitchen.

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| `id` | UUID | PK | |
| `kitchen_id` | UUID | FK kitchens.id, NOT NULL | |
| `invited_by_user_id` | UUID | FK users.id, NOT NULL | Who sent the invite |
| `invited_email` | String(255) | NOT NULL | Email of invitee |
| `token` | String(64) | NOT NULL, Unique, Indexed | Single-use link token |
| `role` | Enum | default='member' | Role when accept |
| `created_at` | DateTime | NOT NULL | |
| `expires_at` | DateTime | NOT NULL | 7 days from creation |
| `accepted_at` | DateTime | Optional | When invitee accepted |
| `accepted_by_user_id` | UUID | FK users.id | User ID of acceptor (may differ from email if another account) |

**Relationships**:
- N Invites : 1 Kitchen

**Validation**:
- invited_email is valid email format
- token is non-empty, unique
- expires_at is ≥ created_at + 1 day
- accepted_at is null until accepted

---

### 10. Conversation & Message

For the Kitchen Assistant chat feature.

| Field (Conversation) | Type | Constraints | Notes |
|-------|------|-------------|-------|
| `id` | UUID | PK | |
| `kitchen_id` | UUID | FK kitchens.id, NOT NULL | |
| `user_id` | UUID | FK users.id, NOT NULL | User who started the conversation |
| `created_at` | DateTime | NOT NULL | |
| `updated_at` | DateTime | NOT NULL | |
| `title` | String(200) | Optional | Auto-generated from first message (v2) |

| Field (Message) | Type | Constraints | Notes |
|-------|------|-------------|-------|
| `id` | UUID | PK | |
| `conversation_id` | UUID | FK conversations.id, NOT NULL | |
| `user_id` | UUID | FK users.id | null if assistant response |
| `content` | Text | NOT NULL | Message text |
| `role` | Enum | NOT NULL | 'user' or 'assistant' |
| `cited_recipe_ids` | UUID Array | Optional | Recipes the assistant mentioned |
| `created_at` | DateTime | NOT NULL | |

**Relationships**:
- N Conversations : 1 Kitchen
- N Messages : 1 Conversation

**Validation**:
- content is non-empty
- role must be 'user' or 'assistant'
- cited_recipe_ids must exist in kitchen (validated in application layer)

---

## Domain Validation Rules (from Spec)

| Requirement | Entity | Rule |
|-------------|--------|------|
| FR-001: Accept recipes in multiple formats | Recipe, Source | Source.type supports 'text', 'url', 'photo' |
| FR-002: Extract ingredients with quantities | RecipeIngredient | quantity ≥ 0, unit required |
| FR-003: Extract cooking instructions | Recipe | instructions required, non-empty |
| FR-004: Structure recipes into schema | Recipe | All mandatory fields required |
| FR-005: Maintain shared ingredient catalog | Ingredient | canonical_name unique per kitchen |
| FR-006: Match ingredient names | RecipeIngredient → Ingredient | Foreign key enforced; no orphans |
| FR-007: Consolidate shopping list | ShoppingList | Derived from recipes; computed on read |
| FR-008: Scale ingredient quantities | ShoppingList.items | quantity_scaled = quantity × (headcount / recipe.yield_servings) |
| FR-009: Answer questions | Conversation, Message | Messages stored with citations |
| FR-010: Role-based access | Member | role enforced in application layer |
| FR-011: Invite members | Invite | Token-based; expires in 7 days |
| FR-012: Persist data durably | All | All have created_at, updated_at, primary keys |
| FR-013: Generate PDFs | ShoppingList | Computed items passed to adapter |
| FR-014: Multi-tenancy | All (except auth) | kitchen_id on all tables |
| FR-015: Audit logs | All | created_at, updated_at track changes (basic audit) |

---

## Indexes & Performance

For optimal queries:

```sql
-- Kitchen
CREATE UNIQUE INDEX idx_kitchens_owner_id ON kitchens(owner_id);
CREATE INDEX idx_kitchens_created_at ON kitchens(created_at);

-- Recipe
CREATE INDEX idx_recipes_kitchen_id ON recipes(kitchen_id);
CREATE INDEX idx_recipes_created_by ON recipes(created_by_user_id);
CREATE INDEX idx_recipes_embedding ON recipes USING ivfflat(embedding vector_cosine_ops);

-- Ingredient
CREATE UNIQUE INDEX idx_ingredients_kitchen_canonical ON ingredients(kitchen_id, LOWER(canonical_name));
CREATE INDEX idx_ingredients_category ON ingredients(category_id);

-- Member
CREATE UNIQUE INDEX idx_members_kitchen_user ON members(kitchen_id, user_id);
CREATE INDEX idx_members_user ON members(user_id);

-- Invite
CREATE UNIQUE INDEX idx_invites_token ON invites(token);
CREATE INDEX idx_invites_kitchen ON invites(kitchen_id);

-- Conversation
CREATE INDEX idx_conversations_kitchen ON conversations(kitchen_id);
CREATE INDEX idx_conversations_user ON conversations(user_id);

-- Message
CREATE INDEX idx_messages_conversation ON messages(conversation_id);
CREATE INDEX idx_messages_user ON messages(user_id);
```

---

## Migrations Strategy

- Use Alembic with auto-migration detection
- Each feature branch introduces migrations
- Migrations must include rollback steps
- Test migrations on a copy of production data (if applicable) before merge
