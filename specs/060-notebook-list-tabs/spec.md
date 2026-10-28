# Feature Specification: Notebook List and Tabs in the UI

**Feature Branch**: `S-060` (branch name is the user's choice; the spec directory is `060-notebook-list-tabs`)

**Created**: 2026-10-25

**Status**: Draft

**Input**: User description: "@dev/docs/backlog.yaml S-060" — Notebook list and tabs in the UI (kitchen page lists its notebooks; personal Notebook tab lists mine). Built on the notebook read answers of spec 056 (S-056).

## Summary

Spec 056 gives every person a default personal notebook and gives every kitchen a kitchen notebook, and it provides the read answers for them. This feature makes those notebooks visible in the app. A signed-in person gets a **Notebook** tab that lists their personal notebooks and marks their default. Every kitchen page gets a section that lists the kitchen's notebooks. Both screens are read-only: nothing here creates, renames, deletes, shares or copies a notebook. It adds no recipe lists (S-021), no capture picker (S-016), no invites (S-057) and no snapshots (S-035).

## Clarifications

### Session 2026-10-25

- Q: Which language should the labels on the Notebook tab and the kitchen notebooks section use? → A: English until the account language setting is built (Story 1.6), then they switch to the person's chosen language.
- Q: When a person taps a notebook on the Notebook tab or the kitchen notebooks section, what should happen? → A: Opens the notebook's recipe list (S-021), once S-021 exists; see FR-014.
- Q: Are notebooks shown as rows or as cards? → A: Cards, shaped like a notebook (not rows).
- Q: Since tapping a card should open the notebook's recipe list, how should this feature handle that list, which is S-021 and not built yet? → A: Keep the tap, but it depends on S-021: cards do nothing until S-021 ships.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - See my personal notebooks on the Notebook tab (Priority: P1)

A signed-in person with an alias opens the Notebook tab. The first time, their default notebook "{alias}'s Notebook" appears, without anyone saying it was created. The tab lists every personal notebook they own or belong to, oldest first. Each notebook appears as a card shaped like a notebook. The card shows the name, the owner's alias (or "unknown"), the person's access (owner or member), and a marker on the default notebook. Kitchen notebooks never appear here.

**Why this priority**: The Notebook tab is where a person first sees where their recipes will be saved. Without it, the notebooks created by spec 056 are invisible, and the capture (S-016) and recipe screens have no place to show them.

**Independent Test**: As a person with an alias and no notebooks, open the Notebook tab, then reopen it. Check that exactly one notebook appears both times, named after the alias, marked as the default, with the person as owner, and that no kitchen page lists it.

**Acceptance Scenarios**:

1. **Given** Ana, alias "ana", who has never opened the Notebook tab, **When** she opens it, **Then** the list shows "ana's Notebook" with access "owner", owner alias "ana", and the default marker.
2. **Given** Ana owns "ana's Notebook" and is a member of Ben's personal notebook "Family", **When** she opens the Notebook tab, **Then** both appear, "Family" shows owner alias "ben" and access "member", and only "ana's Notebook" carries the default marker.
3. **Given** Ben's personal notebook "Family" has lost its owner (owner alias is null), **When** Ana opens the Notebook tab, **Then** the owner shows as "unknown" and the card is otherwise unchanged.
4. **Given** Ana belongs to kitchen "Home", **When** she opens the Notebook tab, **Then** Home's notebook does not appear in the list.

---

### User Story 2 - See a kitchen's notebooks on its page (Priority: P1)

A member opens a kitchen page and sees a notebooks section listing the kitchen's notebooks: name and owner alias (or "unknown"). The first time any member opens the section for a kitchen with no notebook, the notebook is created for them by the same step that lists it, so they see it straight away. When the kitchen is archived, the section still lists its notebooks, but it shows no add-recipe action.

**Why this priority**: The kitchen page is where members will look for the kitchen's recipes, and a kitchen's notebooks are what its recipe list, cart and chat are built from. Showing them is the only way a member can see that a kitchen notebook exists.

**Independent Test**: As Ana, create kitchen "Home" and open its page. Check that exactly one notebook "ana's (Home) Notebook" is listed, owned by Ana. Reload the page and check that the same notebook is listed. Then have Ben, a member, open the page and check he sees the same notebook.

**Acceptance Scenarios**:

1. **Given** Home has no notebook and Ana opens its page, **When** the notebooks section loads, **Then** "ana's (Home) Notebook" is listed as Home's only notebook, with owner alias "ana".
2. **Given** Home has one notebook, **When** Ben, a member, opens its page, **Then** he sees that same notebook, with no duplicate created.
3. **Given** Ana and Ben open Home's page for the first time at the same time, **When** both sections load, **Then** both see the same single notebook.
4. **Given** Home is archived and has notebooks, **When** a member opens its page, **Then** the notebooks are listed and no add-recipe action is shown.
5. **Given** Home is archived and has no notebook, **When** a member opens its page, **Then** the section shows an empty state and no notebook is created.
6. **Given** Carl is not a member of Home, **When** he opens Home's page, **Then** he sees the same not-found state as for a kitchen that does not exist, and no notebook section.

---

### User Story 3 - Lists stay accurate when access changes (Priority: P2)

A person who is removed from a kitchen, or whose access to a notebook ends, stops seeing it on their next visit. Nothing shows stale cards. A person who loads a list that fails sees a clear message and a way to try again, not a partial or empty list that looks like "no notebooks".

**Why this priority**: Access changes are rare today (no route removes members yet), but a list that keeps showing a notebook the person can no longer open would mislead them. The failure message keeps a network problem from looking like missing data.

**Independent Test**: As Ben, a member of Home with its page open, end his membership (or use a test membership change), reload Home's page, and check that the not-found state appears and no notebook is listed. Then make the notebook list fail (for example by stopping the service) and check that a retry message appears instead of an empty list.

**Acceptance Scenarios**:

1. **Given** Ben is a member of Home and has Home's page open, **When** his membership ends and he reloads the page, **Then** he sees the not-found state and no notebook.
2. **Given** the notebooks cannot be loaded, **When** the Notebook tab or a kitchen's section opens, **Then** a message says the notebooks could not be loaded and offers a retry, and no list is shown.
3. **Given** a person has no alias, **When** they open the Notebook tab or a kitchen's notebook section, **Then** they are sent to the existing alias step, and no notebook is shown or created.

---

### Edge Cases

- A person opens the Notebook tab while their default notebook is being created by another request: they see exactly one default, not two.
- Two notebooks share a name (for example two kitchens both called "Home"): both are listed, with their own owner alias; names are not made unique.
- A person changes their alias, or a kitchen is renamed: the notebook names stay as stored, and the owner alias shown is the current one.
- A kitchen notebook's owner leaves the kitchen: the card shows the kitchen owner's alias, as the answer gives it, or "unknown" when none exists.
- A kitchen with notebooks is archived: the page lists them and hides the add-recipe action; a kitchen with none shows an empty state.
- The default notebook was deleted: the Notebook tab shows the replacement default, marked as default.
- A kitchen's list is long: cards are shown in creation order, oldest first, and the page does not hide any card.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The app MUST show a **Notebook** tab in its tab bar to every signed-in person with an alias. Opening it MUST make sure the person's default notebook exists (spec 056 FR-007) before listing their personal notebooks, so the first visit shows the default.
- **FR-002**: The Notebook tab MUST list every personal notebook the person owns or is a member of, and no other. Kitchen notebooks MUST NOT appear in it.
- **FR-003**: Each notebook on the Notebook tab MUST appear as a card shaped like a notebook. The card MUST show the notebook's name, the owner's alias (or "unknown" when none), the person's access ("owner" or "member"), and a default marker on the person's default notebook only.
- **FR-004**: Each kitchen page MUST show a notebooks section listing the kitchen's notebooks to its members. Each notebook MUST appear as a card shaped like a notebook, showing the notebook's name and the owner's alias (or "unknown" when none). Personal notebooks MUST NOT appear in it.
- **FR-005**: Opening a kitchen page's notebooks section as a member MUST make sure the kitchen's first notebook exists when it has none and is not archived (spec 056 FR-008a), and then list it. Repeated and simultaneous openings MUST show the same notebook.
- **FR-006**: When a kitchen is archived, its notebooks section MUST still list its notebooks to members, and MUST NOT show any add-recipe action. An archived kitchen with no notebook MUST show an empty state and create nothing.
- **FR-007**: A non-member, or anyone asking about a missing kitchen, MUST see the same not-found state as for a kitchen that does not exist, and no notebook data.
- **FR-008**: Both screens are read-only. They MUST NOT offer create, rename, delete, invite, member-management or copy controls for notebooks. Those belong to S-059, S-057 and S-048.
- **FR-009**: When notebook data cannot be loaded, the screen MUST show a message that the notebooks could not be loaded, with a retry action, and MUST NOT show a list that looks complete.
- **FR-010**: A person without an alias MUST be sent to the existing alias step from either screen, and nothing MUST be shown or created.
- **FR-011**: Notebook names MUST be shown as stored, without translation or change. Labels on these screens (for example "owner", "member", "unknown", the default marker and the empty and error messages) MUST be in English until the account language setting (Story 1.6) exists, and MUST then follow the person's chosen language.
- **FR-012**: Lists MUST show cards in the order the answer gives them (oldest first), and MUST NOT hide, merge or de-duplicate cards.
- **FR-014**: Tapping a notebook card MUST open that notebook's recipe list once S-021 exists. Until S-021 ships, a notebook card MUST NOT respond to taps and MUST NOT open any recipe list, so FR-013 still holds in this feature (Clarifications 2026-10-25).
- **FR-013**: Neither screen MUST show recipes, categories, cart items or chat content. Those belong to S-016 and later stories.

### Key Entities

- **Notebook (as shown)**: a name, a kind (personal or kitchen), an owner alias or "unknown", and, on the Notebook tab, the person's access and default marker. A kitchen notebook also says which kitchen it belongs to, through its place on the kitchen page. This feature reads notebooks; it does not change them.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: On the first visit to the Notebook tab, a signed-in person with an alias sees their default notebook marked as default, in 100% of automated and manual runs.
- **SC-002**: The Notebook tab shows exactly the personal notebooks a person owns or belongs to, and no kitchen notebook, in 100% of runs.
- **SC-003**: Every member of a kitchen sees the same kitchen notebooks on the kitchen page, and a non-member sees the not-found state, in 100% of runs.
- **SC-004**: When a kitchen with no notebook is first opened by one or more members at the same time, every member sees one and the same notebook, and no duplicate appears, in 100% of runs.
- **SC-005**: No add-recipe action appears on the kitchen page of an archived kitchen, in 100% of runs.
- **SC-006**: Neither screen shows a create, rename, delete, invite or copy control, in 100% of runs.
- **SC-007**: A failed load shows a retry message instead of an empty list, in 100% of runs.
- **SC-008**: A person sees their notebooks within 2 seconds of opening the Notebook tab or a kitchen page on a typical connection.

## Assumptions

- The Notebook tab is added to the existing tab bar next to Home. The kitchen notebooks section sits on the existing kitchen page. Exact layout and placement of the section follow the existing kitchen page and are decided in the plan.
- The add-recipe action on a kitchen page belongs to S-016 (the shared add-recipe component). In this feature the kitchen page has no add-recipe action at all, so the archived rule in FR-006 is a rule for the future action, and this feature only ensures it is not shown in an archived kitchen.
- Lists are short (a person has a handful of notebooks; a kitchen has a few), so no paging or search is needed here.
- The owner alias shown is the current alias the answer gives, not a copy saved on the screen.
- The data is the read answers already defined in spec 056 (personal list, default, kitchen list, one notebook). This feature does not change those answers.
- No per-person interface language exists yet: the account language setting is Story 1.6. Existing pages read the language from a `melos_lang_cache` cookie that defaults to English, and these screens use the same rule, so they show English until that setting exists (FR-011). *(Superseded by spec 063: Spanish and English for every screen, Spanish by default.)*

## Out of Scope

- Creating, renaming or deleting notebooks, and creating more than one personal notebook by hand (S-059).
- Notebook invites and members, including leaving a notebook (S-057).
- Snapshots of a personal notebook into a kitchen, and the origin label (S-035).
- Ownership passing when an account is deleted (S-058).
- Recipe lists, recipe details, capture pickers and the add-recipe action (S-016, S-021, S-027).
- Cart, shopping list, chat and search.
