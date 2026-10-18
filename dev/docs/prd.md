# Melos — Product specification

> Instructions for the coding agent. Build exactly what is described here. If something is ambiguous or missing, **ask before assuming**. Items marked *Should* or *Later* are not built until the *Must* items in [Appendix C](appendix_c_scope_and_schedule.md) are done.

**Problem.** A couple that plans a weekly menu wastes time building the shopping list by hand from several recipes, with quantities that depend on how many people eat.

**User.** A non-technical couple that cooks at home and shops once a week. They keep recipes in their heads, in cookbooks and on websites.

**Goal.** Turn recipes from any source (free text, a web page, a photo of a cookbook page) into structured recipes in a shared kitchen. Then answer questions about them and build a consolidated shopping list scaled to the number of people.

**What the AI does and what it doesn't.**
- The AI structures recipes, matches ingredient names to the kitchen's catalog and answers questions grounded in the kitchen's data.
- Scaling, merging the shopping list and generating PDFs are plain code.

---

## Sections

- **[1. Architecture](1_architecture.md)** — Stack, services, API layers, key flows, data model, AI integration, testing, deployment
- **[2. Customer journey](2_customer_journey.md)** — User flows from account creation through shopping
- **[3. User roles](3_user_roles.md)** — Visitor, Member, Owner capabilities and constraints
- **[4. Disclaimers](4_disclaimers.md)** — Things to avoid: product, data, and coding agent constraints

## Appendices

- **[Appendix A · Entities and CRUD](appendix_a_entities_and_crud.md)** — Full CRUD coverage by entity
- **[Appendix B · Prompts](appendix_b_prompts.md)** — Recipe extractor, kitchen assistant, and TOON encoding
- **[Appendix C · Scope and schedule](appendix_c_scope_and_schedule.md)** — Priority breakdown and delivery milestones (by 02/11/2026)
- **[Appendix D · Open items](appendix_d_open_items.md)** — Decisions yet to be made
