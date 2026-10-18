# Appendix A · Entities and CRUD

> See main PRD at [prd.md](prd.md)

Every entity has full CRUD in the API. The UI only exposes what the journey needs.

| Entity | Create | Read | Update | Delete | In the v1 UI | Notes |
|---|---|---|---|---|---|---|
| User (auth) | register | `/auth/me` | profile; password via reset | `DELETE /auth/me` | all but delete | Deleting the account removes memberships and conversations; kitchens it alone owns are deleted |
| Kitchen | ✓ | ✓ | name, language | owner only | ✓ | Cascades to all its data |
| Membership | via invite | ✓ | role (owner) | leave / remove | ✓ | Last owner protected |
| Invite | owner | owner | resend | revoke | ✓ | |
| Recipe | via draft confirm | ✓ | ✓ | ✓ | ✓ | Update re-embeds |
| Draft | `POST /drafts` | — | — | — | ✓ | Not stored; the response holds the draft |
| RecipeIngredient, Step | nested in Recipe | ✓ | ✓ | ✓ | inside recipe edit | Also addressable at `/recipes/{id}/ingredients`, `/steps` |
| Ingredient | ✓ | ✓ | rename, merge | only if unused | *Should* | `409` if used |
| Category | ✓ | ✓ | rename, merge | ✓ (unlinks) | *Should* | |
| Source | with recipe | ✓ | ✓ | ✓ | link on detail | Deleting keeps the recipe (`source_id` set to null) |
| Cart | with kitchen | ✓ | people | clear | ✓ | One per kitchen |
| CartItem | ✓ | ✓ | meals | ✓ | ✓ | |
| ShoppingList | — | ✓ | — | — | ✓ | **Derived, read-only** |
| RecipeEmbedding | system | system | system | system | — | **Internal, not exposed** |
| Conversation | ✓ | ✓ | title, archive | ✓ | ✓ | Owner user only |
| Message | ✓ (`POST` = ask) | ✓ | — | ✓ | ✓ | **Immutable**, no update |
