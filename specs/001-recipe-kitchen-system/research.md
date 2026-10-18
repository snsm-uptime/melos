# Research: Melos Recipe & Kitchen System

**Phase**: 0 (Unknowns Resolution)  
**Date**: 2026-10-18  
**Status**: Complete

---

## Overview

This document resolves technical unknowns and validates assumptions from the feature spec and implementation plan. All decisions are grounded in the Melos Constitution and finance-dashboard reuse strategy.

## Research Findings

### 1. Recipe Extraction & TOON Encoding

**Unknown**: How to structure recipes for Gemini extraction, and how to encode kitchen context for prompt injection safety?

**Decision**: Use TOON encoding (Text Object Oriented Notation) as defined in Appendix B of the PRD.

**Rationale**: 
- TOON is a fixed, unambiguous format designed for LLM consumption
- Protects against injection by restricting ingredient/category names to a controlled catalog
- The PRD already specifies TOON for both Recipe Extractor and Kitchen Assistant prompts

**Alternatives Considered**:
- JSON schema with free-text fields → risk of LLM-generated injection strings
- Markdown lists → less precise for structured parsing
- TOON ✅ Selected (already specified in PRD)

**Implementation Details**:
- `domain/toon.py`: Implements TOON encoder/decoder
- Kitchen's ingredient and category catalog is serialized as TOON for prompt context
- Recipe output from Gemini is parsed as TOON, validated against kitchen schema

**Reference**: PRD Appendix B (Prompts)

---

### 2. Page Fetching & SSRF Safety

**Unknown**: How to safely fetch and parse recipes from arbitrary URLs without SSRF vulnerabilities?

**Decision**: Use `adapters/web/page_fetcher.py` with network filtering.

**Rationale**:
- Users may provide URLs from any website (internal kitchen networks, private IPs, etc.)
- Must validate URLs against private IP ranges (127.0.0.1, 192.168.x.x, etc.)
- Should honor robots.txt and have request timeouts

**Implementation Details**:
- Blocklist approach: reject URLs targeting 127.0.0.*, 10.0.0.*, 172.16.*.*, 192.168.*.*
- Reject localhost, metadata endpoints (169.254.*, etc.)
- Timeout: 10 seconds max
- User-Agent: "Melos-Recipe-Fetcher/1.0"
- Try schema.org/Recipe JSON-LD first (cleaner extraction); fall back to visible text

**Reference**: finance-dashboard's finance adapter patterns

---

### 3. Ingredient Scaling & Unit Conversion

**Unknown**: Should Melos handle metric ↔ US unit conversion? What about non-linear quantities?

**Decision**: US measurements only in v1; non-linear quantities are user-reviewed.

**Rationale**:
- Target demographic (non-technical home cooks in North America) primarily uses cups, tablespoons, ounces, pounds
- Metric conversion requires complex domain knowledge (density varies by ingredient)
- Non-linear items (e.g., "a pinch of salt," "to taste") don't scale linearly
- Spec success criterion: "Ingredient scaling accurate to within 5% ... for common household quantities"

**Alternatives Considered**:
- Full metric conversion → adds complexity; limited user benefit in v1
- ML-based ingredient-specific conversion → overkill for v1
- User input + validation ✅ Selected for non-linear items

**Implementation Details**:
- `domain/recipe.py`: Unit enum (Cup, Tbsp, Tsp, Oz, Lb)
- `domain/cart.py`: Scaling rules (headcount × quantity for linear items)
- UI flags non-linear ingredients for manual review: "Salt (to taste) — please review"

---

### 4. Shopping List Consolidation & Merging

**Unknown**: How to handle ingredient name variations when consolidating lists?

**Decision**: Use kitchen's ingredient catalog as authority; offer user-guided standardization.

**Rationale**:
- Recipes may reference "flour," "all-purpose flour," "APF" — all mean the same thing
- Kitchen maintains canonical names (e.g., "Flour - All Purpose")
- When new recipes reference variants, system suggests merging or creates new entries

**Implementation Details**:
- `domain/ingredient_catalog.py`: Maintains name normalization rules
- When capturing recipe, Gemini normalizes ingredient names against kitchen catalog
- If recipe references unknown ingredient, system creates it and flags for user review
- `domain/cart.py`: Merges by canonical ingredient name; sums quantities

**Reference**: finance-dashboard's list/split merging logic

---

### 5. Question Answering & Recipe Context (Chat)

**Unknown**: How to ground Kitchen Assistant answers in kitchen state without hallucination?

**Decision**: Use pgvector similarity search + conversation history + kitchen context as TOON.

**Rationale**:
- Embedding similarity finds relevant recipes (cosine distance in pgvector)
- Top-5 results + @mentioned recipes form context
- TOON encoding prevents LLM from inventing ingredients
- Conversation history (last 6 messages) prevents context drift

**Implementation Details**:
- When recipe is saved, its ingredients + instructions are embedded (via Gemini embeddings API)
- Query is embedded; pgvector returns top-5 cosine-similar recipes in kitchen
- Context = top-5 + @mentioned recipes, serialized as TOON
- Gemini ChatModel receives: {question, context, last 6 messages}
- Kitchen Assistant returns: {answer, found, cited_recipe_ids}
- cited_recipe_ids are validated against context; any IDs outside context are dropped

**Reference**: Appendix B (Kitchen Assistant prompt)

---

### 6. PDF Generation & Templates

**Unknown**: What template engine and styling for shopping lists?

**Decision**: WeasyPrint (HTML → PDF) with Jinja2 templates.

**Rationale**:
- WeasyPrint is widely used, supports CSS, and integrates with Python
- Jinja2 is already used in finance-dashboard
- HTML/CSS is flexible for future customization (user-branded shopping lists, multi-format exports)

**Implementation Details**:
- `adapters/pdf/weasyprint.py`: Renders HTML → PDF bytes
- `adapters/pdf/templates/shopping_list.html`: Jinja2 template with CSS
- Template variables: {recipes, ingredients, headcount, generated_at, kitchen_name}
- Future: Markdown export via Markdown library

---

### 7. Authentication & Session Reuse

**Unknown**: Can we reuse finance-dashboard auth fully, or are there Melos-specific changes?

**Decision**: Reuse fully; no Melos-specific changes to auth layer.

**Rationale**:
- Architecture doc specifies auth is reused as-is
- Constitution states: "The authentication layer ... is the security base of the app, so changes to it need explicit approval"
- Email verification and password reset already exist
- Invite-by-email-token flow already exists

**Implementation Details**:
- Use existing endpoints: `/auth/register`, `/auth/sign-in`, `/auth/sign-out`, `/auth/session`, `/auth/me`
- Env var prefix: `MELOS_` (not `FH_`)
- Session cookie: `melos_session` (not `fh_session`)
- On sign-up, create personal kitchen: "My Kitchen"
- Invite acceptance uses same mechanism (create user + join kitchen)

**Reference**: Architecture doc Section 1.3

---

### 8. Multi-Tenancy & Data Isolation

**Unknown**: How strict is kitchen-level isolation? Can Owners see members' private notes?

**Decision**: Kitchen is the isolation boundary; all user data is kitchen-scoped.

**Rationale**:
- Spec: "Members and Owners operate on shared kitchen data"
- Constitution II: "Kitchen is the source of truth; members operate on shared kitchen data"
- Members can see all recipes, ingredients, and shopping lists in their kitchen
- Future: Personal notes/preferences are out of scope for v1

**Implementation Details**:
- Every table except `auth_users`, `auth_sessions` has `kitchen_id`
- Access control in `application/` layer: verify user is kitchen member before returning data
- Non-members get `404` (not `403`) — don't reveal kitchen existence
- Follows finance-dashboard list access pattern

---

### 9. Error Handling & Recipe Extraction Failures

**Unknown**: What happens if recipe extraction fails (malformed input, Gemini error)?

**Decision**: Return RecipeDraft with error state; user reviews and edits or retries.

**Rationale**:
- Recipes may be incomplete, non-English, or corrupted images
- Should never silently fail or skip recipes
- User has full control: can edit extracted data or cancel

**Implementation Details**:
- `domain/recipe.py`: ParseResult{is_recipe: bool, reason: str, draft: RecipeDraft | None}
- If `is_recipe=False`, `reason` explains why (e.g., "Detected as a shopping list, not a recipe")
- UI shows draft (even if error) for user to review/edit
- If user saves, any missing fields trigger validation errors (FR-002, FR-003 enforcement)

---

### 10. Role Model & Permission Boundaries

**Unknown**: Are there edge cases between Visitor/Member/Owner roles?

**Decision**: Three roles only; permissions are clear. See spec User Story 5.

**Rationale**:
- Spec defines Visitor (view), Member (add/edit recipes), Owner (manage kitchen + members)
- No moderator, admin, or guest roles in v1
- Constitution V: "Role boundaries verified; permission model changes are tested"

**Implementation Details**:
- `domain/membership.py`: Role enum (Visitor, Member, Owner)
- In `application/`, every use case checks: `if role not in [required_roles]: raise PermissionError`
- Tests verify: Owner can invite, Member can add recipes, Visitor can only view

---

## Unknowns Resolution Summary

| Unknown | Decision | Status |
|---------|----------|--------|
| Recipe extraction & TOON encoding | Use TOON as per PRD Appendix B | ✅ Resolved |
| Page fetching & SSRF safety | URL validation + timeout | ✅ Resolved |
| Ingredient scaling | Linear US measurements; user reviews non-linear | ✅ Resolved |
| Shopping list consolidation | Canonical names + kitchen catalog | ✅ Resolved |
| Question answering | Embeddings + pgvector + TOON context | ✅ Resolved |
| PDF generation | WeasyPrint + Jinja2 | ✅ Resolved |
| Authentication reuse | Full reuse; no Melos-specific changes | ✅ Resolved |
| Multi-tenancy isolation | Kitchen-scoped; 404 for non-members | ✅ Resolved |
| Recipe extraction errors | RecipeDraft with error state; user reviews | ✅ Resolved |
| Role model & permissions | Visitor/Member/Owner; clear boundaries | ✅ Resolved |

---

## Next Phase

Phase 1: Design will generate:
- `data-model.md`: Entity definitions, relationships, validation rules
- `contracts/api.md`: REST endpoint specifications
- `contracts/domain.md`: Domain model shapes (Recipe, Ingredient, etc.)
- `contracts/ui.md`: Page layouts and component responsibilities
- `quickstart.md`: End-to-end validation workflow

All research findings are incorporated into design decisions above.
