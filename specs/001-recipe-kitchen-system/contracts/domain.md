# Domain Model Contract: Melos Recipe & Kitchen System

**Phase**: 1 (Design)  
**Date**: 2026-10-18  
**Status**: Draft

---

## Overview

This contract defines the shapes and behaviors of core domain entities as they exist in the application layer. See `data-model.md` for database schema; this document describes the domain logic and validation rules.

## Entity Shapes

### Recipe

```python
class Recipe:
    id: UUID
    kitchen_id: UUID
    title: str  # 1-200 chars
    instructions: str  # non-empty, may include markdown
    yield_servings: int  # >= 1
    cook_time_minutes: Optional[int]  # >= 0
    prep_time_minutes: Optional[int]  # >= 0
    difficulty: Enum['easy', 'medium', 'hard']
    created_by_user_id: UUID
    created_at: DateTime
    updated_at: DateTime
    
    @property
    def total_time(self) -> Optional[int]:
        """Computed: cook_time + prep_time"""
        ...
    
    @property
    def embedding(self) -> Vector:
        """pgvector embedding; computed on save"""
        ...
    
    def validate(self) -> List[str]:
        """Return validation errors (empty if valid)"""
        ...
```

### RecipeIngredient

```python
class RecipeIngredient:
    id: UUID
    recipe_id: UUID
    ingredient_id: UUID  # FK to Ingredient
    quantity: Decimal  # > 0
    unit: str  # from allowed list: cup, tbsp, tsp, oz, lb, ml, l, g, kg, unit
    notes: Optional[str]  # e.g., "(to taste)", "(melted)"
    is_linear: bool  # if False, user reviews when scaling
    
    def scale(self, scale_factor: float) -> RecipeIngredient:
        """Return scaled copy (quantity *= scale_factor)"""
        ...
    
    def validate(self) -> List[str]:
        """Return validation errors"""
        ...
```

### Ingredient

```python
class Ingredient:
    id: UUID
    kitchen_id: UUID
    canonical_name: str  # unique per kitchen, 1-100 chars
    category_id: UUID
    aliases: List[str]  # ["flour", "all-purpose", "APF"]
    unit: str  # default unit
    
    def matches(self, name: str) -> Tuple[bool, float]:
        """(matched, confidence_0_to_1) - check if name matches canonical or aliases"""
        ...
    
    def add_alias(self, alias: str) -> None:
        """Add variant name to aliases (deduplicate)"""
        ...
    
    def validate(self) -> List[str]:
        """Return validation errors"""
        ...
```

### Kitchen

```python
class Kitchen:
    id: UUID
    name: str  # unique per owner, 1-100 chars
    owner_id: UUID
    created_at: DateTime
    updated_at: DateTime
    timezone: str  # default 'UTC'
    content_language: Enum['en', 'es']
    
    def is_member(self, user_id: UUID) -> bool:
        """Check if user is owner, member, or visitor"""
        ...
    
    def get_role(self, user_id: UUID) -> Enum['owner', 'member', 'visitor']:
        """Get user's role in this kitchen"""
        ...
    
    def can_edit_recipe(self, user_id: UUID, recipe_id: UUID) -> bool:
        """Owner can edit any recipe; member can edit own recipes (v2)"""
        ...
    
    def validate(self) -> List[str]:
        """Return validation errors"""
        ...
```

### ShoppingCart (Derived)

```python
class ShoppingCart:
    """Derived from recipes + headcount; not persisted"""
    recipes: List[Recipe]
    headcount: int  # >= 1
    
    @property
    def items(self) -> List[CartItem]:
        """Consolidated, scaled ingredients"""
        # 1. For each recipe, get RecipeIngredients
        # 2. Scale by (headcount / recipe.yield_servings)
        # 3. Group by ingredient_id, sum quantities
        # 4. Sort by category, then ingredient name
        ...
    
    def validate(self) -> List[str]:
        """Recipes exist, headcount >= 1"""
        ...

class CartItem:
    ingredient: Ingredient
    quantity: Decimal
    unit: str
    recipes_using: List[Recipe]
    notes: Optional[str]  # e.g., "to taste (review manually)"
```

### ParseResult (from RecipeExtractor)

```python
class ParseResult:
    is_recipe: bool
    reason: Optional[str]  # if not a recipe, explain why
    draft: Optional[RecipeDraft]

class RecipeDraft:
    title: str
    instructions: str
    yield_servings: int
    cook_time_minutes: Optional[int]
    prep_time_minutes: Optional[int]
    difficulty: str
    ingredients: List[DraftIngredient]
    source: SourceMetadata

class DraftIngredient:
    name: str  # extracted name (not yet matched to catalog)
    quantity: Decimal
    unit: str
    notes: Optional[str]
    is_linear: bool
```

## Domain Rules

### Recipe Extraction (RecipeExtractor Port)

**Input**: Recipe source (text, URL, or image)  
**Output**: ParseResult

**Rules**:
1. If source is URL, fetch & parse (SSRF-safe)
   - If schema.org/Recipe JSON-LD present, map to RecipeDraft
   - Else, extract visible text and send to Gemini
2. If source is image, send to Gemini (multimodal)
3. If source is text, send to Gemini
4. Gemini returns TOON-encoded recipe
5. Parse TOON; if valid, return ParseResult{is_recipe=True, draft=...}
6. If validation fails (missing fields, invalid units, etc.), return ParseResult{is_recipe=False, reason="..."}
7. Ingredient names are extracted but not yet matched to kitchen catalog
   - Matching happens on save (application layer)

### Shopping List Consolidation (Cart Domain)

**Input**: List of recipes, headcount  
**Output**: Consolidated, scaled cart items

**Rules**:
1. For each recipe in list:
   - Get all RecipeIngredients
   - For each ingredient, scale quantity:
     - `scaled_quantity = quantity × (headcount / recipe.yield_servings)`
   - If ingredient.is_linear == False, flag for user review (don't auto-scale)
2. Group all ingredients by ingredient_id
3. For each ingredient_id, sum all scaled quantities
4. Return sorted by:
   - Category (Produce, Dairy, Pantry, ...)
   - Then by Ingredient.canonical_name

**Non-Linear Handling**:
- Items with `is_linear=False` are included in list but quantity=0 (or original)
- UI displays note: "Salt (to taste) — please review"
- User must manually enter quantity

### Ingredient Normalization (IngredientCatalog Domain)

**Input**: Raw ingredient name from recipe  
**Output**: Matched Ingredient or new Ingredient

**Rules**:
1. Query kitchen's ingredient catalog for matches:
   - Exact match (case-insensitive) to canonical_name
   - Fuzzy match to aliases (if confidence > 0.85)
2. If match found, use matched Ingredient.id
3. If no match, create new Ingredient:
   - canonical_name = cleaned input name
   - aliases = [input name] (if different from canonical)
   - category = inferred or default to "Other"
4. Return Ingredient.id for recipe linking

### Question Answering (ChatModel Port)

**Input**: Question, optional @mentioned recipes, conversation history (last 6 messages)  
**Output**: Answer + found flag + cited_recipe_ids

**Rules**:
1. Embed question via Embedder
2. Query pgvector for top-5 cosine-similar recipes in kitchen
3. Context = top-5 ∪ @mentioned recipes (as TOON)
4. Send to Gemini ChatModel:
   - System prompt: "You are a helpful kitchen assistant. Answer only from the context below."
   - Context: TOON-encoded recipes + categories
   - Conversation history (last 6 messages)
   - User question
5. Gemini returns: {answer, cited_recipe_ids}
6. Validate cited_recipe_ids exist in context; drop any outside
7. Return response with valid citations

## Validation Rules (from Spec)

| Entity | Rule | Error |
|--------|------|-------|
| Recipe | title non-empty, ≤200 | "Title required" |
| Recipe | yield_servings >= 1 | "Yield must be at least 1" |
| Recipe | instructions non-empty | "Instructions required" |
| Recipe | at least 1 RecipeIngredient | "At least 1 ingredient required" |
| RecipeIngredient | quantity > 0 | "Quantity must be positive" |
| RecipeIngredient | unit in allowed list | "Invalid unit" |
| Ingredient | canonical_name unique per kitchen | "Ingredient already exists" |
| Kitchen | name non-empty, ≤100 | "Kitchen name required" |
| Kitchen | only 1 owner | "Kitchen already has an owner" |
| ShoppingCart | recipes exist | "One or more recipes not found" |
| ShoppingCart | headcount >= 1 | "Headcount must be at least 1" |

## Computed Fields

| Entity | Field | Computation |
|--------|-------|-----------|
| Recipe | total_time | cook_time_minutes + prep_time_minutes |
| Recipe | embedding | Embedder(instructions + ingredients) |
| ShoppingCart | items | (consolidate & scale RecipeIngredients) |
| CartItem | recipes_using | (back-reference recipes in cart) |

---

See `data-model.md` for database schema details.
