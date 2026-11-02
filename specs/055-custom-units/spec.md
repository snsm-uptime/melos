# Feature Specification: Custom Units and Admin Dashboard

**Feature Branch**: `055-custom-units`

**Created**: 2026-11-01

**Status**: Draft

**Input**: User description: "I want to manage cases where the AI didn't identify a unit, for example if a person says "una lata de frijoles" lata is not recognized. The goal is to interact with the user for them to validate if they want to consider that a unit from now on. this will be added to the list of units for their account. In the database, I want the units table, with a name and a user id that references who added it. that table has the default values (with user = system). The idea is that users can only query the default units and others that match with the ID but the admin user could see all unique units on the table. This is to later add logic that defines a value as "system" if more than 5 distinct users have it. /speckit-clarify let's talk about the best data model since the users only query this when a recipe is added or edited but the admin or dashboards might query the whole table (although this may not happen often either)"

## Clarifications

### Session 2026-11-01

- Q: How should the units table record who owns a unit, including the system defaults? → A: One table with one row per unique name. Each row holds `user_references` as a native list of user ids, a count computed by the database from that list, and an `is_default` flag. There is no promoted flag. The count covers active accounts only, so a deleted account leaves the list.
- Q: How should the app know who the admin is, given it has no admin today? → A: An `is_admin` flag on the user account, false by default. The owner approved this change to the auth table.
- Q: What should the admin get, and should the dashboard be built inside this units feature or as its own story? → A: Inside this feature: a page showing all unit columns, ingredient metadata, recipe metadata and user activity.
- Q: Since a recipe is always in exactly one notebook, what should "how many notebooks" show on the dashboard? → A: The recipe's notebook name, its kind (personal or kitchen) and how many people can open it. Nothing new is stored.
- Q: What should "activity" mean in the users section of the dashboard? → A: Existing data (open sessions, the newest session's start, recipes authored, the date of their latest recipe) plus how many times a person created, edited and closed a cart. No login tracking is added.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Keep a new unit found in a capture (Priority: P1)

A person pastes a recipe that says "una lata de frijoles". The draft shows that "lata" is not one of their units and asks if they want to use it as a unit from now on. They say yes, finish reviewing and save. The line reads "1 lata frijoles" and "lata" is now on their list of units.

**Why this priority**: This is the feature. Today the person can only fix the line by hand, and the word they used is lost.

**Independent Test**: Capture a recipe with one unknown unit on a fresh account, accept the question, save, and confirm the recipe line keeps the word and the account's unit list now has it.

**Acceptance Scenarios**:

1. **Given** a recipe text with "una lata de frijoles" and "lata" is not on the person's list, **When** the draft opens, **Then** the line shows the word "lata" and asks whether to keep it as a unit.
2. **Given** the question is showing, **When** the person accepts and saves the recipe, **Then** the recipe is saved with "lata" on that line and "lata" joins their list.
3. **Given** the question is showing, **When** the person declines, **Then** the line stays flagged and they pick one of their units or turn the amount into a vague note, as they must today, and "lata" does not join their list.
4. **Given** the person accepted, **When** they discard the draft, **Then** nothing is saved and "lata" does not join their list.
5. **Given** a recipe with "lata" on three lines and "latas" on another, **When** the draft opens, **Then** the person is asked about "lata" once and the answer applies to all four lines.
6. **Given** a recipe with two unknown words, **When** the draft opens, **Then** each word gets its own question and can be answered differently.

---

### User Story 2 - The unit is known from then on (Priority: P1)

Having kept "lata", the person is not asked again. Later captures accept it, and the recipe add and edit screens offer it next to the default units.

**Why this priority**: Without this the person's answer has no lasting value.

**Independent Test**: After Story 1, capture a second recipe with "2 latas de atún" and open a recipe for editing. No question appears, and "lata" can be picked.

**Acceptance Scenarios**:

1. **Given** "lata" is on the person's list, **When** they capture a recipe with "2 latas de atún", **Then** the line reads quantity 2, unit "lata", with no question and no flag.
2. **Given** "lata" is on the person's list, **When** they add or edit a recipe by hand, **Then** "lata" is offered along with the default units.
3. **Given** a person editing a recipe by hand types a word that is not on their list, **When** they leave the field or save, **Then** they get the same question as in a capture.
4. **Given** two accounts, **When** one keeps "lata", **Then** the other's list does not change and that person is still asked about "lata" in their own captures.

---

### User Story 3 - Shared recipes keep working for everyone (Priority: P2)

Recipes are shared in notebooks and kitchens, while units belong to one account. A kitchen member who never kept "lata" can still read, scale, edit, copy and shop from a recipe that uses it.

**Why this priority**: The couple cooking from one kitchen is the product's core use. A unit one of them added must never break the other's cart or shopping list.

**Independent Test**: With person A's recipe using "lata" in a shared kitchen, person B opens it, scales it, edits the title, and adds it to the cart. Nothing fails, and B's own list does not change.

**Acceptance Scenarios**:

1. **Given** a recipe that uses "lata" in a shared notebook, **When** a member without "lata" on their list reads it, **Then** the line reads "1 lata frijoles".
2. **Given** that same member edits another part of the recipe, **When** they save, **Then** the "lata" line stays as it is and they are not asked about it.
3. **Given** that member changes the unit on that line, **When** the picker opens, **Then** it shows their own units plus the line's current unit.
4. **Given** two recipes in the cart with 1 lata and 2 latas of frijoles, **When** the shopping list is built, **Then** it shows 3 lata of frijoles on one line.
5. **Given** a scaled recipe that needs 1.5 lata of frijoles, **When** the shopping list is built, **Then** it shows 2 lata, rounded up the way counted items are.
6. **Given** frijoles in the cart as 1 lata and as 200 g, **When** the shopping list is built, **Then** both amounts show with no conversion between them.
7. **Given** a recipe using "lata", **When** a member copies it to another notebook or snapshots the notebook, **Then** the copy keeps "lata", and the person's list does not change.

---

### User Story 4 - See how the app is used (Priority: P3)

The admin opens a dashboard with four sections: units, ingredients, recipes and users. The units section is also the input for a later rule that makes a unit a default for everyone when more than 5 distinct people have it.

**Why this priority**: It serves the product owner, not cooks, and no cooking flow depends on it.

**Independent Test**: With several accounts holding overlapping units, ingredients and recipes, open the dashboard as the admin and as a normal account, then compare the admin's figures to the known data.

**Acceptance Scenarios**:

1. **Given** "lata" kept by 3 people and "bote" by 1, **When** the admin opens the units section, **Then** each name appears once with every stored field, including its references, and counts of 3 and 1.
2. **Given** "tomate" in 4 recipes by 2 different authors, **When** the admin opens the ingredients section, **Then** "tomate" appears once with 4 recipes and 2 people, whichever notebooks hold it.
3. **Given** a recipe added to carts 5 times, **When** the admin opens the recipes section, **Then** it shows that recipe's title, 5, its notebook's name and kind and how many people can open it, and no ingredients or steps.
4. **Given** an account without `is_admin`, **When** it asks for the dashboard or its data, **Then** it gets a not-found answer and learns nothing.
5. **Given** "lata" kept by 3 people, **When** one of them deletes their account, **Then** "lata" counts 2.
6. **Given** any section, **When** the admin reads it, **Then** no conversation content appears.
7. **Given** a person who filled an empty cart, changed it and pressed Done on its list, **When** the admin opens the users section, **Then** that person shows 1 created, 1 edited and 1 closed, while the other kitchen members show none.

---



- **Word already covered**: a word that maps to a default unit, or is one of its known spellings ("taza", "caja", "pieza"), keeps mapping to that unit and is never offered as new.
- **Vague amounts**: "una pizca", "al gusto" and similar stay vague notes and are never offered as units.
- **Near misses**: the existing rule for a word one letter away from a known spelling still applies, and it also covers the person's own units, so "latta" maps to their "lata". A word close to two different units is still invalid output.
- **Countable items with no unit**: "2 huevos" stays quantity 2, unit "unit". Only a real measure word is offered.
- **A later default**: a promoted unit is the same row, so the person's list shows it once.
- **Race**: two people confirming the same word at once both end up on its one row, and the same person confirming from two tabs counts once, with no error.
- **Size**: a size belongs only to the count unit, so "una lata grande" keeps "lata" and does not record a size.
- **Long or odd input**: a word over 32 characters, empty after trimming, or holding only digits or symbols is not offered as a unit.
- **Account deleted**: the person leaves each unit's references and its count drops by one. A non-default unit left with no references is removed. Recipes that use the word keep it, and the unit never turns into a default because of the deletion.
- **AI gives no measure word**: if the AI folds "una lata" into a plain count, nothing is lost silently, because the extraction must report the measure word it read (FR-002).
- **Archived kitchen**: no capture happens there, so no question is asked.

## Requirements *(mandatory)*

### Functional Requirements

**Recognizing and asking**

- **FR-001**: Each person's available units MUST be the default units plus the units on their own account, and nothing else.
- **FR-002**: Extraction MUST report a measure word from the source text that is outside the person's available units, rather than dropping it or folding it into a plain count.
- **FR-003**: Normalization MUST trim, lower-case and make the word singular before it is compared or stored, as with ingredient names, so "Latas" and "lata" are one unit.
- **FR-004**: The draft MUST show each unknown word once, with the lines it affects, and ask the person if they want to keep it as a unit from now on.
- **FR-005**: If the person accepts, the word MUST join their list when the recipe is saved, in the same action as the save. A discarded draft MUST add nothing.
- **FR-006**: If the person declines, the line MUST stay flagged until they pick an available unit or make the amount a vague note. Declining MUST NOT be remembered: the same word asks again next time.
- **FR-007**: A recipe MUST NOT be saved with a line whose unit is neither available to the person nor already on that stored line.
- **FR-008**: A word covered by FR-001, a vague phrase, or a size MUST NOT trigger the question.

**Using the units**

- **FR-009**: Capture MUST recognize the person's own units with no question, the same way it recognizes defaults, for pasted text and web pages.
- **FR-010**: The recipe add and edit screens MUST offer the person's available units, and a new word typed there MUST get the question in FR-004.
- **FR-011**: The person's list MUST be read only when adding or editing a recipe. Reading a recipe MUST NOT depend on it.
- **FR-012**: A recipe line MUST keep its unit as written, independent of who holds that unit. Changing or deleting an account's units MUST NOT change any recipe.
- **FR-013**: Reading, scaling, copying, snapshots, the cart and the shopping list MUST accept any unit stored on a line, whoever views it.
- **FR-014**: On the shopping list, amounts of the same ingredient in the same custom unit MUST add up and round up to a whole number. Different units MUST never be converted into each other.
- **FR-015**: Custom units MUST show as stored in every language, and the question itself MUST exist in Spanish and English.
- **FR-016**: Hand-added shopping list items keep the default units only.

**Oversight**

- **FR-017**: An admin MUST be able to open a dashboard with units, ingredients, recipes and users sections. It is read-only and reached from a place only admins see.
- **FR-017a**: An account MUST be an admin only when its `is_admin` flag is set. The flag is false for every new account, no request can change it, and it is set on the server by the owner.
- **FR-017b**: The units section MUST show every stored field of every unit, including `user_references`.
- **FR-017c**: The ingredients section MUST show each normalized name once across all notebooks, with the number of unique recipes using it and the number of distinct people who authored those recipes.
- **FR-017d**: The recipes section MUST show each recipe's title, the number of times it was added to a cart, its notebook's name and kind (personal or kitchen), and how many people can open that notebook. It MUST NOT show the recipe's ingredients or steps.
- **FR-017e**: The users section MUST show, for each account: open sessions, the newest session's start date, recipes authored, the date of their latest recipe, and how many times they created, edited and closed a cart, with the date of their latest such action.
- **FR-017f**: The app MUST record the person and time of each cart action from this feature on, in the same action as the change. A person "creates" a cart when they add the first recipe to an empty cart, "edits" it when they save any later change, and "closes" it when they press Done on the shopping list. Nothing before this feature is counted, and an account's records go with the account.
- **FR-018**: A non-admin MUST NOT be able to read any other account's units through the unit list, or anything on the dashboard. A unit may still be visible on a shared recipe.
- **FR-019**: The dashboard MUST NOT show conversation content, recipe ingredients or steps, password data or session tokens.
- **FR-020**: The data MUST let a later feature count distinct people per unit name and make a name a default. That rule itself is out of scope here.
- **FR-020a**: The count on a unit MUST always equal the number of active accounts in its references, computed by the data store with no separate step.
- **FR-020b**: Deleting an account MUST remove it from every unit's references in the same action as the deletion, so no id of a deleted person is kept. A non-default unit with no references left MUST be removed.

**Safety**

- **FR-021**: A stored unit MUST be treated as data. When sent to the AI it follows the same delimiting rule as recipe text, and it can never act as an instruction.

### Key Entities

- **Unit**: a name a person can use as a measure, one row per unique name. It has `user_references` (the active accounts that kept it), a count of those accounts, and `is_default` (true for everyone's units). The ten seeded defaults, g, kg, oz, lb, ml, l, cup, tbsp, tsp and unit, are default with no references. A later promotion only sets `is_default` on the existing row. A person's list is every default plus every unit that references them.
- **Cart activity**: one record of a person creating, editing or closing a cart, with its time. It exists only for the dashboard, and no cart behaviour reads it.
- **Recipe line**: keeps its unit as plain text, as it keeps its ingredient name, so it depends on no account.
- **Unknown unit question**: part of the draft, not stored. A word, the lines it affects and the person's answer, carried until save or discard.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A person can accept an unknown unit and save the recipe without retyping the line.
- **SC-002**: After a unit is kept, every later capture with that word needs no question and no fix.
- **SC-003**: With two accounts, 0 of one account's units appear in the other's list in any flow.
- **SC-004**: Every default-unit recipe saved before this feature reads, scales and shops exactly as before.
- **SC-005**: A recipe with a custom unit can go through read, scale, edit, copy, cart and shopping list for a member who never kept that unit, with no failure.
- **SC-006**: Dashboard figures match the true data in 100% of test cases, and an account without `is_admin` gets nothing from it.

## Assumptions

- This specifies backlog story S-055, redirected. It replaces the story's earlier design: no separate trial table or background job, a word joins on the person's yes, and the later threshold is more than 5 distinct people (not more than 3). The story's maintainer review step moves to the later promotion story.
- Promotion to default is out of scope, as are renaming or removing a kept unit, and any list screen for managing units.
- No way to delete an account exists yet (S-054). As with S-058, this feature delivers the removal in FR-020b as a rule that account deletion calls in its own transaction, and S-054 must not ship without it. Nobody sees a change until then.
- Custom units are never converted and have no mass or volume. They act like counted items: they scale, add up and round up on the shopping list.
- Display uses the stored singular form ("3 lata"). Plural display is not part of this feature.
- The MCP service has no capture tool yet, so it needs no question flow. When one is added, it has to refuse or flag unknown units, as it cannot ask here.
- Sessions cannot show cart actions or login history: a cart keeps only its last editor, closing records nobody, and logging out removes the session. A person who only browses looks inactive, and that is accepted.
- Recipe titles on the dashboard are a deliberate exception to PRD §3, which keeps a personal notebook readable only by its owner and members. The PRD text changes with this feature. The rule that nobody reads another person's conversations stands.
- Login, sessions and passwords are unchanged. The only change to the auth layer is the `is_admin` column on `users`, which the owner approved on 2026-11-01 (constitution §1).
- PRD §1.6, §2 J2 and Appendix B, and AGENTS.md, describe the fixed list of ten units, and PRD §3 says there is no in-app admin. Those texts need updating with this feature.
