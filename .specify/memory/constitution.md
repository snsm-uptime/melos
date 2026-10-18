<!-- Sync Impact Report (remove before commit)
Version: 0.1.0 → 1.0.0 (MINOR: initial constitution for v0 branch)
Added: All core principles and governance
Modified: None (initial version)
Removed: None
Follow-up: None
-->

# Melos Constitution

## Core Principles

### I. User-Centric Non-Technical Design
Every feature exists to serve non-technical home cooks planning weekly meals. Design decisions
prioritize usability over technical elegance; when in doubt, choose the path that requires less
explanation to a household without coding experience. Account creation, recipe capture, and
shopping list generation must feel natural to users who keep recipes in cookbooks and heads,
not code.

### II. Kitchen as Source of Truth
The shared kitchen is the authoritative hub. All recipes are structured into the kitchen's
catalog; ingredients reference the kitchen's standardized names; questions about what's
available or needed are answered from kitchen state. Members and Owners operate on shared
kitchen data; conflicts are resolved by ownership, not by duplicate catalogs.

### III. AI Structures, Code Scales
AI integration is bounded and explicit: Recipe Extractor structures free-form recipes into
our schema; Kitchen Assistant answers questions grounded in kitchen data. Plain code handles
everything else: recipe scaling by headcount, merging duplicate ingredients across multiple
recipes, generating PDFs, and consolidating shopping lists. AI does not make decisions about
ingredient substitution, meal suitability, or user preferences.

### IV. Contracts Before Implementation
Data contracts—recipe schema, ingredient catalog structure, kitchen entity definitions—are
documented before code is written. Changes to contracts require explicit approval and migration
planning. This protects recipes (user's most valuable data) and prevents silent data loss when
structures change.

### V. Role-Based Access with Clear Boundaries
Visitor, Member, Owner are distinct roles with documented capabilities. Visitors can view
shared recipes but not edit; Members can add/edit recipes in the kitchen they're invited to;
Owners manage the kitchen (add members, delete recipes, configure). Permission logic is
testable and auditable; ambiguous cases are escalated as design issues before implementation.

## Development Workflow

Melos uses **feature-driven branches** off main. Each feature is owned by a developer, tested
before merge, and reviewed for contract compliance. Speckit drives the workflow: start with
`/speckit-specify` to document requirements, then implement and verify against the spec.
Breaking changes to the kitchen schema require constitution amendment before merge.

## Quality Gates

- **No schema changes without amendment**: Changes to core entities (Kitchen, Recipe,
  Ingredient, ShoppingList) require updating this constitution first.
- **AI contracts explicitly documented**: Prompts and expected outputs are in Appendix B of
  the PRD; changes to prompt behavior or model selection require spec update and review.
- **Role boundaries verified**: Permission model changes are tested and documented before
  merge; ambiguity is resolved in the feature spec, not at code-review time.

## Governance

This constitution is the law of the Melos project. All PRs must verify compliance before
merge. Amendments require:

1. Documented rationale (what changed and why—e.g., new role, new constraint, or clarified
   principle)
2. Impact analysis (which existing features or workflows are affected)
3. Migration plan if breaking (how do existing kitchens/recipes adapt)
4. Version bump per semantic versioning rules (MAJOR: incompatible changes; MINOR: new
   principle/section; PATCH: clarifications)

Runtime development guidance is documented in `AGENTS.md`; this constitution supersedes
that file when they conflict.

**Version**: 1.0.0 | **Ratified**: 2026-10-18 | **Last Amended**: 2026-10-18
