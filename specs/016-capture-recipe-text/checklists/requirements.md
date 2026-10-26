# Specification Quality Checklist: Capture a Recipe from Pasted Text

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-10-20
**Updated**: 2026-10-22 (re-sync with spec 015 and the PRD)
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] No implementation details (languages, frameworks, APIs)
- [x] Focused on user value and business needs
- [x] Written for non-technical stakeholders
- [x] All mandatory sections completed

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain
- [x] Requirements are testable and unambiguous
- [x] Success criteria are measurable
- [x] Success criteria are technology-agnostic (no implementation details)
- [x] All acceptance scenarios are defined
- [x] Edge cases are identified
- [x] Scope is clearly bounded
- [x] Dependencies and assumptions identified

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria
- [x] User scenarios cover primary flows
- [x] Feature meets measurable outcomes defined in Success Criteria
- [x] No implementation details leak into specification

## Notes

- 2026-10-20, iteration 1: all items passed.
- 2026-10-22, re-sync: categories changed from "3 to 5, kitchen first" to the controlled lists (0–2 main ingredients, 0–2 cuisines, International fallback); input limit 10,000 characters; two-recipe message "Upload only one recipe at a time"; Picture opens nothing; estimated servings default to 4; one attempt per submission; the J3 ownership conflict is closed in the PRD.
- 2026-10-22, Q1 answered: the call to action goes on a new bottom-bar Recipes tab (per-user page) and on a Recipes tab on the kitchen page (FR-001, FR-001a, FR-001b). Follow-up answer: recipes live in notebooks, one per member and one shared per kitchen; a capture is for the notebook it started from (FR-001a, FR-003, FR-022). Replaces the last-opened-kitchen assumption. Data-model gap (no per-member ingredient catalog in the PRD) recorded in Assumptions for S-020 and S-018.
- 2026-10-22, Q2 = A: Discard only; storing unique vague amounts moves to S-020 (FR-019; notes added to spec 015 and backlog S-020).
- 2026-10-22, Q3: "Assistant misconfigured. Your text is kept" (User Story 3 scenario 4, FR-028; spec 015 contract marked approved).
- 2026-10-22: ingredients belong to a member or a kitchen; a personal capture reuses the member's personal catalog (FR-003). Copy into a kitchen and normalization (kitchen names win) assigned to S-020 and S-018.
- 2026-10-22, notebooks course correction: copies drift apart; kitchen recipes belong to the kitchen with an author; kitchen captures save to the kitchen and the member's notebook. PRD, AGENTS.md, backlog (new S-035, S-019 moved after S-025) and spec 015 updated. Spec 016 requirements unchanged apart from FR-001a and Assumptions.
- Final pass: all items pass; no [NEEDS CLARIFICATION] markers remain.
- 2026-10-25, re-sync with the notebook redesign (2026-10-23) and spec 056's snapshot model: spec.md body now uses personal and kitchen notebooks, a notebook picker for the capture, no automatic personal copy, and the capture's notebook catalog (FR-001a, FR-003, FR-022, Key Entities, Assumptions). All items re-checked: all pass; no [NEEDS CLARIFICATION] markers. plan.md, tasks.md, research.md, data-model.md and contracts/ still describe the 2026-10-22 model and need their own re-sync before /speckit-plan or /speckit-implement.
- Component names (`AddRecipeCallToAction`, `ActionDialog`, `Sheet`) appear only in Assumptions, as the reuse rule AGENTS.md requires. Category file paths are named because they are the product's controlled vocabulary.
