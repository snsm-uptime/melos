# Feature Specification: Scheduled Ingredient Translation Service

**Feature Branch**: `worktree-jobs`

**Created**: 2026-11-07

**Status**: Draft

**Input**: User description: "I'm not using the mcp project for anything, instead of it, I want another python server that is for cronjobs. I want it in the docker compose to use the private network and have access to the db container and to have centralized logs. I want to have a background job that every hour runs a query to validate if any new ingredients were added to the database. Ingredients now have a field that defines the language in the same way as the application setting. This way if an ingredient was added on an english recipe, after the job runs, there would be a spanish entry for that ingredient translated by AI. all ingredients from people's notebooks now become a centralized list after a model has the value translated, this way the catalog increases it's quality, consistency and internationalization."

## Clarifications

### Session 2026-11-07

- Q: Should AI-translated ingredient entries be saved automatically or only after a person confirms them? → **Answered: option A.** AI-validated translations are saved without confirmation, marked as AI-made, and reused across people (FR-005a, FR-020). Requires a constitution exception to Principle 5.
- Q: Does the central list replace the per-notebook and kitchen catalogs, or sit alongside them? → **Answered (revised): alongside.** The per-notebook and kitchen catalogs keep their current logic. A new central standard table holds the validated, translated values, and the job adds every name that has not been processed yet (FR-007, FR-016). Recipe lines keep their names, as they do today.
- Q: Who may rename, merge or split a standard (central) ingredient? → **Answered: no one through the app.** Standard names change only when the job adds them (FR-021).
- Q: When the AI saves a wrong translation, who may edit or delete it? → **Answered:** a person who sees a wrong or missing name in the agent's output types their own value for their notebook, as today. The AI-made standard entry is flagged, and the admin dashboard lists each such value for validation. If the admin accepts a value, it is added to the standard table (FR-022).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Hourly detection of new ingredients (Priority: P1)

Once an hour, a background job looks at the ingredient names that people have added to their recipes since the last run. Each name that the standard table has not yet processed is recorded there with the language of the recipe it came from. Names that were already processed are left alone.

**Why this priority**: Every other part of the feature depends on knowing which ingredients are new. Without detection, there is nothing to translate or standardize.

**Independent Test**: Add a recipe in English that contains an ingredient the standard table has never seen, wait for the next hourly run (or trigger it manually), and confirm the ingredient is recorded once with language `en`. Run the job again and confirm no duplicate is created.

**Acceptance Scenarios**:

1. **Given** a recipe in English with the ingredient "bell pepper" that the standard table does not yet have, **When** the hourly job runs, **Then** "bell pepper" is recorded in the standard table with language `en`.
2. **Given** the same ingredient was already recorded, **When** the job runs again, **Then** no new entry is created and the existing entry is unchanged.
3. **Given** no new ingredients were added since the last run, **When** the job runs, **Then** it finishes without changes and logs that nothing was found.

---

### User Story 2 - AI translation into the other language (Priority: P1)

When the job records an ingredient in one language, it asks an AI model to validate the name and give the equivalent name in the other supported language, and stores that translation as a second entry for the same standard ingredient. An ingredient added on an English recipe therefore gets a Spanish entry, and an ingredient added on a Spanish recipe gets an English entry.

**Why this priority**: Translation is the core value: it gives every standard ingredient a name in both languages, so people in either language see the same ingredient.

**Independent Test**: Add an English recipe with "onion". After the job runs, confirm that a Spanish entry exists for it (for example "cebolla") linked to the same standard ingredient.

**Acceptance Scenarios**:

1. **Given** a newly recorded English ingredient "onion", **When** the translation step runs, **Then** a Spanish entry "cebolla" is stored for the same standard ingredient.
2. **Given** a translation was already stored for an ingredient in that language, **When** the job runs again, **Then** no second translation is requested or stored.
3. **Given** the AI model fails or times out for one ingredient, **When** the job processes a batch, **Then** the other ingredients in the batch are still processed, the failure is logged, and the failed ingredient is retried on the next run.
4. **Given** a standard ingredient "onion" was already translated to Spanish when another person added it, **When** that person's recipe is saved, **Then** no AI call is made; the existing translation is reused.

---

### User Story 3 - Standard ingredient table next to the notebook catalogs (Priority: P2)

A standard table holds one entry per real-world ingredient, with its validated names in both languages. It sits next to the per-notebook and kitchen catalogs, which keep working as they do today. Names from every notebook feed the standard table, so the catalog grows in quality, consistency and internationalization across all notebooks.

**Why this priority**: This is the long-term goal, but it depends on detection and translation working first, and it adds a second table next to the existing catalogs.

**Independent Test**: Two people in different notebooks each add "tomato" in different spellings. After the job runs, the standard table holds one entry for tomato with its Spanish and English names, and each notebook's own catalog is unchanged.

**Acceptance Scenarios**:

1. **Given** two notebooks add "tomatoes" and "tomato", **When** the job runs, **Then** the standard table holds one ingredient, not two.
2. **Given** a notebook's catalog already has its own names, **When** the job runs, **Then** those names are not changed or removed; only the standard table is added to.

---

### User Story 4 - Operations: private service with centralized logs (Priority: P2)

The job runs as its own service in the existing Docker Compose stack. It reaches the database over the private network only, is not exposed on a host port, and writes its logs to the same place as the other services so that one place shows what ran and what failed.

**Why this priority**: Required for the job to run safely in the stack, but the feature can be verified manually before it runs on a schedule.

**Independent Test**: Start the stack, confirm the job service is up with no published port, confirm it can read the database, and confirm its log lines appear with the other services' logs.

**Acceptance Scenarios**:

1. **Given** the stack is running, **When** the job service connects to the database, **Then** it succeeds over the internal network without a host port being published.
2. **Given** the job runs, **When** an operator looks at the centralized logs, **Then** each run shows its start, the number of ingredients found, translated, and failed, and its end time.
3. **Given** the database is not yet ready at startup, **When** the job service starts, **Then** it waits for the database and does not crash-loop.

---

### Edge Cases

- What happens when an ingredient name is written in a language the app does not support? It is recorded with its detected language if known, and it is not translated; it is logged for review.
- What happens when the job runs while a previous run is still going? The second run does nothing and logs that the previous run is still active, so the same ingredient is never translated twice.
- What happens when the AI returns an empty or unusable translation? Nothing is stored for that language, the failure is logged, and the ingredient is retried on the next run.
- What happens when the same ingredient is added in both languages on the same day? The two names resolve to one standard ingredient and no duplicate translations are created.
- What happens when a person deletes an ingredient from their notebook? The standard entry is kept; only the notebook's own catalog entry changes.
- What happens when the mcp service is removed and something still calls it? The call fails with a clear "service removed" response; nothing in the stack depends on it.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST run a background job every hour that finds ingredient names added to any notebook since the previous successful run and that the standard table has not yet processed.
- **FR-002**: Each ingredient name MUST carry a language, using the same values as the application's language setting (`en` or `es`), taken from the language of the recipe it was added to.
- **FR-003**: The system MUST record each new name once in the standard table, keyed by its normalized form (trimmed, lower-case, singular), and MUST NOT create duplicates on repeated runs.
- **FR-004**: For each newly recorded ingredient, the system MUST request a translation into the other supported language from an AI model and store the result as an entry linked to the same standard ingredient.
- **FR-005**: The system MUST NOT request or store a second translation for the same standard ingredient and language.
- **FR-005a**: A translation MUST be requested at most once per standard ingredient and language, shared by every notebook. A name that is already in the standard table with its other-language entry MUST NOT trigger any AI call.
- **FR-006**: If the translation fails or returns nothing usable, the system MUST store nothing for that language, log the failure, and retry the ingredient on the next run.
- **FR-007**: Ingredient names from every notebook MUST feed the standard table. The per-notebook and kitchen catalogs MUST keep their current logic and are not replaced.
- **FR-008**: The job service MUST run as a separate service in the Docker Compose stack, on the internal network, with no host port published.
- **FR-009**: The job service MUST have read and write access to the database service and MUST NOT be reachable from outside the stack.
- **FR-010**: The job service MUST send its logs to the same centralized log output as the other services, and each run MUST log its start, end, and counts of found, translated, and failed ingredients.
- **FR-011**: The job service MUST wait for the database to be ready at startup and MUST NOT stop if the database is not ready on the first attempt.
- **FR-012**: Only one run of the job may be active at a time.
- **FR-013**: The mcp service MUST be removed from the Docker Compose stack and from the repository, along with anything that only exists to support it, once the new job service is in place.
- **FR-014**: Secrets, including the AI model key, MUST come from environment configuration only and MUST NOT be written into the code or the image.
- **FR-015**: The translation model name MUST come from configuration, not be hard-coded.
- **FR-018**: Each embedded entity (recipe, ingredient, notebook, kitchen, cart and cart history) MUST keep its vector in its own table keyed by the entity's id. Vector rows MUST NOT store lists of related ids.
- **FR-020**: A translation that the AI model has validated MUST be saved without a person's confirmation, and MUST be marked as AI-made so it can be found and reviewed later.
- **FR-021**: Standard names MUST NOT be renamed, merged or split through the app by any person. Standard names enter the table only through the job (FR-003, FR-004).
- **FR-022**: A person MAY enter their own value for an ingredient in their notebook when the name in the agent's output is wrong or missing, as today. When that value replaces an AI-made standard entry, the entry is flagged, and the value appears on the admin dashboard as a name to validate (admin = `users.is_admin`, spec 055). Only the admin can accept or reject it. An accepted value is added to the standard table with its translation. A rejected value stays in the notebook catalog only.

### Key Entities *(include if feature involves data)*

- **Standard Ingredient**: One real-world ingredient in the centralized standard table. It has a kept name and is the target of all translations. It is separate from the per-notebook and kitchen catalogs.
- **Standard Ingredient Name**: A name of a standard ingredient in one language, with its language, its normalized text, and whether it was written by a person (admin-accepted) or produced by the translation job. One standard ingredient has at most one name per language.
- **Ingredient Discovery Record**: The record that a name was seen in a notebook, with its source language and the run in which it was first found.
- **Admin Review Item**: A flagged value awaiting the admin's decision, with the AI-made entry it replaces, the person who entered it, and the decision.
- **Job Run**: One hourly execution, with its start and end time, counts of found, translated and failed names, and its outcome.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Every ingredient added to any recipe appears in the standard table within 1 hour of being added.
- **SC-002**: 100% of standard ingredients have a name in both supported languages once the next hourly run after their creation has finished, except those that failed and are being retried.
- **SC-003**: A repeated run with no new ingredients creates zero new entries and zero translation requests.
- **SC-004**: At least 95% of translation attempts succeed on the first run; the remainder are retried and succeed within 3 hourly runs.
- **SC-005**: Every hourly run leaves a complete log record with start, end, and counts, visible in the centralized logs.
- **SC-006**: The job service has no host-published port, and every connection to the database is made over the internal network.
- **SC-007**: After the change, the stack starts with no mcp service and every remaining service's health check still passes.

## Assumptions

- **Two supported languages**: The app supports English (`en`) and Spanish (`es`). A new name is translated into the other one. More languages are out of scope.
- **Language setting**: The ingredient language uses the same values and the same meaning as the existing recipe language field (spec 043), so a name's language is the language of the recipe it came from.
- **Catalogs**: The per-notebook and kitchen catalogs keep their current rules (AGENTS.md domain rules). The standard table is a new table next to them, not a replacement.
- **Recipe lines**: Recipe lines keep carrying the name, as they do today. This feature does not add an ingredient id to them.
- **Hourly cadence** is a fixed schedule, not a user setting, for the first version.
- **AI provider**: The translation uses the same Gemini API and key the app already uses, through the existing configuration. No other AI provider is added.
- **Removing mcp**: The user has said the mcp project is not used. The mcp service and its endpoints are removed, not kept as a fallback. The AI-provider endpoints described in AGENTS.md are assumed to have no users.
- **Constitution impact**: Principle 1 and Principle 7 fix the stack at four services with no worker. Replacing mcp with a scheduled job service changes that, so a constitution amendment is needed before implementation. The project lead approves the amendment (constitution Amendment Procedure).
- **Privacy**: Ingredient names are not personal data. A recipe's text, author and notebook membership stay private to their notebook; only ingredient names feed the standard table.
- **Logs**: "Centralized logs" means the logs of all services are collected in one place by the existing Compose logging setup. A separate log platform is out of scope.

## Open Questions

### Q1: Resolved — save AI translations automatically (option A)

Decided 2026-11-07. AI-validated translations are saved without confirmation and marked as AI-made (FR-020). This conflicts with constitution Principle 5 ("An AI draft is never saved without the user confirming it first"), so the Principle 5 wording needs an explicit exception, approved by the project lead under the Amendment Procedure, before implementation.

### Q2: Resolved (revised) — standard table sits alongside the notebook catalogs

Decided 2026-11-07, revised the same day. The per-notebook and kitchen catalogs keep their current logic. A centralized standard table holds the validated, translated values, and the job adds every name it has not yet processed (FR-007). This replaces the earlier decision to make the central list the only catalog. The AGENTS.md domain rule on per-notebook catalogs does not change.

## Out of Scope

- More than two languages.
- Translating recipe text, instructions, or titles (only ingredient names).
- A user interface for reviewing translations beyond the admin dashboard list in FR-022.
- Changing the hourly schedule through the app.
- Reverse proxy, TLS and server configuration (owned separately, per Principle 7).
