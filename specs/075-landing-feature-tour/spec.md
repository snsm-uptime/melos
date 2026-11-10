# Feature Specification: Landing page feature tour

**Feature Branch**: `075-landing-feature-tour`

**Created**: 2026-11-10

**Status**: Draft

**Input**: User description: "I want to redesign the landing page and improve the feature demos. Give the full perspective of what the app does. For this, first centralize all user features into a list. Group related features and give them a section on the landing page, this way, users get a walkthrough of the main features"

## Context

Today the signed-out landing page has a hero (logo, one-line intro, "Create an account" and
"Sign in") and three static cards: Kitchens, Recipes and Shopping. The cards name a few
features in one sentence each and show no example of the app at work. Most of what the app
does (photo and web capture, notebooks, sharing, shopping by store, the ingredient catalog,
two languages) is not mentioned. The shopping card is also titled "Shopping kitchen" in English
and "Cocina de compras" in Spanish, a copy slip for "shopping list" / "lista de compras".

This story first writes down every feature a person can use in one **feature inventory**, then
groups the inventory into a few **feature groups**, and gives each group its own section on the
landing page with a short **demo**. A visitor who scrolls the page gets a walkthrough of the app,
in the order they would use it.

### Feature inventory (first draft, from the done stories up to 2026-11-10)

| Group | Feature | Story |
|---|---|---|
| 1. Capture any recipe | Paste a recipe's text and get a structured draft | S-016 |
| | Capture from a web page link (a site that refuses gets its own message) | S-026, S-069 |
| | Capture from a photo of a cookbook page | S-041 |
| | Review the draft before saving; clear messages name what is missing | S-016, S-017 |
| | Ingredient names are matched to your catalog, and you are told what changed | S-018 |
| | Units the app does not know are confirmed by you once | S-055 |
| | Quick add from anywhere in the app | S-069 (quick add) |
| 2. Your recipe notebooks | Personal notebooks: a default one, create, rename, delete | S-056, S-059, S-060 |
| | Recipe page with image, edit and delete | S-027, S-067 |
| | Scale servings to see amounts for more or fewer people | S-062 |
| | Find recipes with a text filter, sort and search tables | S-021, S-066 |
| 3. Cook together | Kitchens, shared or solo, with email invites | S-009, S-011 |
| | Kitchen notebooks every member reads and writes | S-056 |
| | Share a personal notebook by invite | S-057 |
| | Add a copy of a personal notebook to a kitchen | S-035 |
| | Send a recipe to a person | S-071 |
| 4. Plan the week and shop | Cart: pick recipes, set people and meals | S-022 |
| | One consolidated shopping list with amounts added up, and which recipe each line is for | S-023 |
| | Saved list with hand-added items, closed when done | S-025 |
| | Shop by store: store tabs, mark items bought | S-070 |
| 5. Ingredients that stay tidy | One ingredient catalog per notebook | S-018, S-020 |
| | Rename, merge and split ingredient names | S-043 |
| | Each ingredient in English and Spanish | S-043, S-073 |
| 6. Made for your home | Spanish or English, every screen translated | S-063 |
| | Profile with alias, photo and light or dark theme | S-005 |

Planned features (marked planned in the inventory, shown only in the "Coming soon" strip, FR-004):

| Feature | Story |
|---|---|
| Ask the kitchen assistant about your recipes | S-029, S-030 |
| Search recipes by meaning, not just words | S-044 |
| Recipe PDF | S-028 |
| Export the shopping list | S-024 |
| Paste a receipt to check off what was bought | S-068 |

## Clarifications

### Session 2026-11-10

- Q: What kind of demo should each landing section show? → A: Animated scenes built in the app's own look with invented data; they play when scrolled into view, can be paused, and stay still under reduced motion (not screenshots, videos or a hands-on sandbox).
- Q: Should the landing page also show features that are not built yet? → A: Yes, as a short "Coming soon" strip at the end that names the planned features, with no demos; group sections list only available features.
- Q: Are the six groups, in the proposed order, the walkthrough wanted? → A: Yes: Capture any recipe, Your recipe notebooks, Cook together, Plan the week and shop, Ingredients that stay tidy, Made for your home.
- Q: Should the top of the page be redesigned too? → A: Full redesign: a new headline, a new intro, and a short overview animation that plays the whole flow from capture to shopping list; the account buttons stay.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Walk through what the app does (Priority: P1)

A visitor who has never used Melos opens the landing page. Below the hero, the page shows one
section per feature group, in the order a person uses the app: capture, notebooks, cooking
together, planning and shopping, ingredients, and home settings. Each section has a short title,
one or two plain sentences, the list of features in the group, and a demo. At the end, the page
asks them again to create an account or sign in.

**Why this priority**: This is the request: give the visitor the full picture of the app. Without
it, the redesign has no purpose.

**Independent Test**: Open the landing page signed out. Scroll from top to bottom and check that
every available feature in the inventory appears in exactly one section, in the group order above,
and that the account buttons appear at the top and the end.

**Acceptance Scenarios**:

1. **Given** a visitor who is not signed in, **When** they open the landing page, **Then** they see
   the redesigned hero with its new headline, "Create an account", "Sign in" and the overview demo,
   followed by six feature sections in the inventory's group order.
2. **Given** the landing page, **When** the visitor reaches the last feature section, **Then** a
   closing call to action offers "Create an account" and "Sign in" again.
3. **Given** a person who is signed in, **When** they open the landing page address, **Then** they
   are sent to their usual starting page as today, and do not see the tour.
4. **Given** the English landing page, **When** the visitor reads the shopping section, **Then** it
   speaks of a "shopping list", never a "shopping kitchen".

---

### User Story 2 - See each feature group at work in a demo (Priority: P1)

Each section shows a demo: a short, self-playing scene of the app's own screens with invented
example data, that shows the before and after of the group's main feature. For example, the
capture demo shows a pasted recipe with "a pinch of salt" and "2 large onions" becoming a draft
where salt has a vague note and onion reads "2 unit large"; the shopping demo shows recipe A with
3 tbsp flour and recipe B with 1 cup flour becoming one line, "flour — 1 cup + 3 tbsp", with chips
A and B.

**Why this priority**: The user asked to improve the demos. Seeing the result is what makes a
visitor understand a feature faster than reading about it.

**Independent Test**: Open each section and watch its demo play once from start to end; check that
it shows the stated before and after, with no real personal data, and that it can be paused.

**Acceptance Scenarios**:

1. **Given** a feature section that comes into view, **When** its demo starts, **Then** it plays its
   scene and loops, and a visible control pauses and resumes it.
2. **Given** a visitor whose device asks for reduced motion, **When** they view a section, **Then**
   the demo shows its final state as a still picture and does not move.
3. **Given** a demo, **When** it plays, **Then** it uses only invented example recipes, names and
   amounts, and makes no request to capture or save anything.
4. **Given** a demo, **When** a screen reader reaches it, **Then** it reads a text description of
   what the demo shows.

---

### User Story 3 - Jump to the feature group I care about (Priority: P2)

A visitor who only cares about one thing, for example shopping, can jump straight to that section
from a short index of the six groups near the top of the page.

**Why this priority**: Useful for a long page, but the walkthrough works without it.

**Independent Test**: Choose each entry in the index and check the page moves to that section and
the address can be shared to open the page at that section.

**Acceptance Scenarios**:

1. **Given** the landing page, **When** the visitor chooses "Plan the week and shop" in the index,
   **Then** the page moves to that section.
2. **Given** an address that points to a section, **When** it is opened, **Then** the page opens at
   that section.

---

### User Story 4 - Read the tour in my language (Priority: P2)

A Spanish-speaking visitor sees the whole tour, section titles, texts, feature lists and demo
content in Spanish; an English visitor sees it in English, chosen the same way the landing page
chooses its language today (spec 063, Spanish by default).

**Why this priority**: The app is Spanish by default; an English-only tour would break that rule.

**Independent Test**: Open the page with each language and check that no text, including the demo
scenes and their descriptions, appears in the other language.

**Acceptance Scenarios**:

1. **Given** a visitor with no saved language, **When** they open the landing page, **Then** every
   section and demo is in Spanish.
2. **Given** a visitor whose language resolves to English, **When** they open the page, **Then**
   every section and demo is in English.

---

### User Story 5 - Keep the inventory and the page in step (Priority: P3)

When a story that adds or changes a feature a person can use is done, the person who finishes it
updates the feature inventory, and the landing page follows from the inventory: a new available
feature appears in its group's list without redesigning the page.

**Why this priority**: Keeps the tour honest over time; the first release works without it.

**Independent Test**: Add an invented available feature to the inventory in a test, and check it
appears in its group's list on the page, in both languages.

**Acceptance Scenarios**:

1. **Given** the inventory, **When** a feature is added to a group with both an English and a
   Spanish description, **Then** it appears in that group's section.
2. **Given** a feature in the inventory marked planned, **When** the page is shown, **Then** it
   appears only in the "Coming soon" strip, not in its group's section (FR-004).

---

### Edge Cases

- A group whose demo fails to load or play: the section still shows its title, text and feature
  list, and the demo area shows its still final state or nothing, never an error.
- A very narrow phone (320 px wide): sections stack, demos fit the width, and the page has no
  sideways scrolling.
- A visitor who opens the page signed in on another tab and comes back: the existing "redirect if
  signed in" behaviour still applies.
- A feature in the inventory with a description in only one language: it is not shown, and a test
  fails, so it cannot ship half translated.
- A visitor who scrolls fast past sections: demos that are out of view do not play.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The project MUST keep one feature inventory: every feature a signed-in person can use,
  each with a group, a short name and one plain sentence in English and in Spanish, the story or
  stories that build it, and a status: available or planned.
- **FR-002**: The inventory MUST group features into the six groups listed in Context, in that order.
  A feature belongs to exactly one group.
- **FR-002a**: The hero MUST be redesigned: a new headline and intro that sum up the app, the
  "Create an account" and "Sign in" buttons, and an overview demo, a short animated scene (same
  rules as FR-006 to FR-010) that plays the whole flow once: a recipe captured, saved to a
  notebook, added to the cart, and shown as a line on the shopping list. The overview demo plays on
  page load (no scrolling needed) and, like every demo, can be paused and is still under reduced
  motion.
- **FR-003**: The landing page MUST show, below the hero, one section per group, in group order. Each
  section shows the group title, one or two sentences, the list of the group's available features,
  and a demo.
- **FR-004**: Group sections MUST list only features marked available. Features marked planned MUST
  appear only in a short "Coming soon" strip after the last group section and before the closing
  call to action: their names and one sentence each, with no demos and no dates. When a planned
  feature becomes available, it moves from the strip to its group. With no planned features, the
  strip is not shown.
- **FR-005**: The section's feature list MUST come from the inventory, so adding an available
  feature to the inventory shows it on the page with no other change.
- **FR-006**: Each section MUST have a demo: a short animated scene drawn in the app's own look
  (not a screenshot, video or recording, and not a hands-on sandbox), with invented data, showing the before and after of the group's main feature. The six scenes are:
  1. Capture: a pasted recipe (and a link and a photo as inputs) becoming a reviewed draft, with
     "a pinch of salt" shown as vague and "2 large onions" as "2 unit large".
  2. Notebooks: a notebook of recipe cards, one opened, servings scaled from 4 to 2 and the amounts
     changing.
  3. Cook together: a kitchen with two members and their notebooks, and a recipe being sent to a
     person.
  4. Plan and shop: two recipes added to the cart, and the shopping list showing
     "flour — 1 cup + 3 tbsp" with chips A and B, then items marked bought on a store tab.
  5. Ingredients: "onions" and "onion" merged into one name, shown as "cebolla" in Spanish.
  6. Home: the same screen switching from Spanish to English and from light to dark.
- **FR-007**: A demo MUST start when its section comes into view, loop, and have a visible control to
  pause and resume it. A demo out of view MUST NOT play.
- **FR-008**: When the visitor's device asks for reduced motion, every demo MUST show its final state
  as a still picture.
- **FR-009**: Each demo MUST have a text description readable by screen readers, in the page's
  language.
- **FR-010**: Demos MUST NOT call the app's capture, AI or save features, and MUST NOT use real
  personal data.
- **FR-011**: The page MUST offer a short index of the six groups near the top; each entry moves the
  page to its section, and each section has its own address that opens the page at it.
- **FR-012**: The page MUST end with a closing call to action with "Create an account" and
  "Sign in".
- **FR-013**: All landing text, feature lists and demo content MUST be in English and Spanish, with
  the language chosen as today (spec 063). A feature or text missing either language MUST fail a
  test.
- **FR-014**: A signed-in visitor MUST keep being redirected to their starting page as today.
- **FR-015**: The page MUST work from 320 px wide up to desktop with no sideways scrolling, in light
  and dark themes, with the app's current palette.
- **FR-016**: The shopping text MUST say "shopping list" in English and "lista de compras" in
  Spanish; "Shopping kitchen" and "Cocina de compras" MUST NOT appear.
- **FR-017**: When a story that adds, removes or changes a feature a person can use is done, its
  done note MUST say whether the inventory was updated. The rule is written at the top of the
  inventory; adding it to the AGENTS.md backlog rule as well needs the owner's explicit approval
  (AGENTS.md, Amendments to Governance).

### Key Entities

- **Feature group**: one of six themes of the app, in a fixed order; has a title and one or two
  sentences in English and Spanish, and one demo.
- **Feature**: one thing a person can do in the app; belongs to one group; has a short name and a
  sentence in English and Spanish, the stories that build it, and a status (available or planned).
- **Demo**: a short self-playing animated scene, one per group plus one overview demo in the hero,
  with invented example data, a still final state,
  and a text description in English and Spanish.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of available features in the inventory appear in exactly one group section, and
  100% of planned features appear only in the "Coming soon" strip.
- **SC-002**: The landing page names at least 20 features, up from about 9 today.
- **SC-003**: In a walk-through with 3 people who have not used the app, each can name at least 4 of
  the 6 groups after scrolling the page once, in under 3 minutes.
- **SC-004**: Every group demo plays its full scene in under 15 seconds, and the overview demo in
  under 20 seconds; every demo shows a still final state under reduced motion.
- **SC-005**: 0 untranslated strings in either language, checked by a test.
- **SC-006**: The page has no sideways scrolling at 320 px wide, and every section is reachable from
  the index in one choice.

## Assumptions

- The audience is visitors who are not signed in; signed-in people never see the page (unchanged).
- "Feature demos" means the landing page's feature cards; there is no other demo page today. The
  demos are built from the app's own look with invented data, not screen recordings and not a
  live sandbox, so they stay in step with the palette, cost nothing to run, and never touch real
  data.
- The inventory is kept in the repository as the single source both for the landing page and for
  people working on the app. Its exact place and format are for the plan.
- The inventory's first draft (Context) comes from the done stories up to 2026-11-10; the plan
  checks it against the running app. Admin-only features (admin dashboard, review list) are left
  out, because visitors will not use them.
- The six groups and their order were confirmed by the owner on 2026-11-10.
- Only the landing page and its text change. Sign up, sign in and the auth layer keep working as
  today, and the hero's account buttons keep their destinations. No new data is stored.
- The story needs a backlog entry (S-075, epic Platform, priority should) before it is built.
