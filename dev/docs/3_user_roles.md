# 3. User roles

> See main PRD at [prd.md](prd.md)

| Role | Who | Can |
|---|---|---|
| **Visitor** | Not signed in | Landing page, sign up, sign in, password reset, open an invite link |
| **Member** | Belongs to a kitchen | Full CRUD on the kitchen's recipes, ingredients, categories, sources and cart. CRUD on **their own** conversations. Leave the kitchen |
| **Owner** | Created the kitchen, or was promoted | Everything a Member can do, plus: rename the kitchen, change `content_language`, invite and remove members, promote/demote, delete the kitchen |

- Roles are per kitchen: the same user can be an Owner in one kitchen and a Member in another.
- No user can read another user's conversations, including Owners.
- There is no in-app admin. Operations (backups, logs) happen on the server.
