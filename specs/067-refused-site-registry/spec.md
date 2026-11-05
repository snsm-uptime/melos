# Feature Specification: Refused Site Registry

**Feature Branch**: `067-refused-site-registry`

**Created**: 2026-11-04

**Status**: Draft

**Input**: User description: "for this types of errors, add a table of domains that give these types of issues and write the messages they provide into a column. also use an exception for "This website requires a license, it's not supported yet". the idea is that when the admin sees user frequently using a website, the consideration to get the license is done."

## Context

Recipe capture by link (spec 026) shows one generic "the page could not be opened" message for every failure. Some sites, such as allrecipes.com, answer on purpose with a refusal page (HTTP 402) that asks automated readers to license the content. The member cannot tell this from a broken link, and nobody running Melos learns which licensed sites members want.

This feature treats a refusal from the site itself as its own outcome. The member gets a clear message, and each refusal is recorded per domain, with the text the site sent back, so the admin can see how much demand each site has.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Member is told the site needs a license (Priority: P1)

A member pastes a link to a site that refuses automated reading. The capture fails with "This website requires a license, it's not supported yet" instead of the generic message.

**Why this priority**: This fixes the confusion that started the request. On its own it already tells the member to stop retrying and to use text or a photo instead.

**Independent Test**: Capture a link whose site answers with a refusal status. The member sees the license message. A link that times out or does not exist still shows the generic message.

**Acceptance Scenarios**:

1. **Given** a site that answers a capture with a refusal status (see FR-001), **When** a member captures a link to it, **Then** the capture fails with "This website requires a license, it's not supported yet", in the member's language, and no draft is created.
2. **Given** a link that fails for any other reason (timeout, unknown host, blocked address, not HTML, too large, server error), **When** a member captures it, **Then** they see the existing generic message, unchanged.
3. **Given** a site that answers with a refusal, **When** the member sees the message, **Then** it contains none of the site's own page text, no status code and no address.

---

### User Story 2 - Refusals are recorded per domain (Priority: P1)

Every refusal adds to a record for the site's domain. The record keeps the count, how many different members hit it, when it was first and last seen, the last status, and the message the site returned.

**Why this priority**: Without this record the admin cannot see demand, and that demand is the reason for the feature.

**Independent Test**: Capture links on one refusing domain several times from two accounts. The domain's record shows the right total, 2 distinct members, the right dates and the site's message text.

**Acceptance Scenarios**:

1. **Given** no record for a domain, **When** its first refusal happens, **Then** a record is created with count 1, 1 distinct member, first seen = last seen = now, the status, and the site's message.
2. **Given** an existing record, **When** another refusal happens, **Then** the count goes up by one, last seen and last status are updated, and the stored message is replaced by the newest one.
3. **Given** the same member refused twice on one domain, **Then** the total count is 2 and the distinct member count stays 1.
4. **Given** links on `www.allrecipes.com` and `allrecipes.com`, **Then** both count toward a single `allrecipes.com` record.
5. **Given** failures that are not refusals, **Then** no record is created or changed.

---

### User Story 3 - Admin reviews the refused sites (Priority: P2)

The admin opens a "Refused sites" section of the existing dashboard (spec 055). It lists each domain with its counts, dates, last status and the site's message, sorted by most-used first, so the admin can decide whether to pursue a license.

**Why this priority**: The data is only useful once someone can read it. It comes after P1 because records can pile up before the view ships.

**Independent Test**: With seeded records, open the dashboard as the admin and check the order and values. Open it as a normal account and get the dashboard's usual not-found answer.

**Acceptance Scenarios**:

1. **Given** several records, **When** the admin opens the section, **Then** domains are listed by total count, highest first, showing domain, total, distinct members, first seen, last seen, last status and message.
2. **Given** a non-admin account, **When** it asks for the section or its data, **Then** it gets the same not-found answer as the rest of the dashboard.
3. **Given** a site message that contains markup or script, **When** the admin views it, **Then** it shows as plain text and nothing in it runs.

### Edge Cases

- **Redirect, then refusal**: the record goes to the domain that refused, not the one in the pasted link.
- **Empty or non-text refusal page**: the record is still counted and the message is left empty.
- **Huge refusal page**: only the readable text is kept, trimmed to 1,000 characters.
- **Race**: two refusals for the same new domain at the same moment end up as one record with count 2.
- **Rate limiting (429)**: treated as a temporary failure, so the member sees the generic message and nothing is recorded.
- **Account deleted**: its past refusals stay in the totals. The record never stored who the member was, so no identity is kept.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A capture MUST be treated as a site refusal when the site answers the page request, after any redirects, with status 401, 402, 403 or 451. Every other failure keeps its current handling.
- **FR-002**: On a site refusal the member MUST see "This website requires a license, it's not supported yet" (and its Spanish translation), shown as its own error, separate from the generic page-not-opened error.
- **FR-003**: The member-facing message MUST NOT include the site's text, the status code, the address or anything technical (keeps spec 026 FR-024). Refusals for blocked or private addresses MUST still show the generic message so the network cannot be probed.
- **FR-004**: Each refusal MUST update one record per registrable domain (for example `allrecipes.com`, without `www.` or other subdomains), in the same step as the capture's answer. A failure to record MUST NOT change what the member sees.
- **FR-005**: A record MUST hold: domain, total refusals, distinct members refused, first seen, last seen, last status, and the newest site message.
- **FR-006**: The site message MUST be stored as plain readable text taken from the refusal page (markup, scripts and styles removed, whitespace collapsed), trimmed to 1,000 characters. It is data only and is never shown to members or passed to any AI step.
- **FR-007**: The distinct-member count MUST be kept without storing a lasting link from the record to any member account, or anything else that identifies who tried.
- **FR-008**: Records MUST NOT store the link's path, query or any other part of the URL beyond the domain.
- **FR-009**: The admin dashboard MUST show a read-only "Refused sites" section with the fields from FR-005, sorted by total refusals, highest first. Only admins can reach it, as with the rest of the dashboard.

### Key Entities

- **Refused site**: one domain that has refused captures. Domain (unique), total refusals, distinct members, first seen, last seen, last status, last message.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of captures refused by the site with a status from FR-001 show the license message. 0% of other failures do.
- **SC-002**: After N refusals from M distinct members on one domain, the record shows exactly N and M.
- **SC-003**: An admin can name the 5 most-requested refusing sites in under 30 seconds after opening the dashboard.
- **SC-004**: No member-facing response and no stored record contains a URL path, a member identity or an internal address.
- **SC-005**: A refused capture answers no slower than it does today, within normal variation.

## Assumptions

- "These types of errors" means the site deliberately refusing automated reading, as allrecipes.com does with 402. Timeouts, server errors and rate limits are out of scope.
- The admin is the existing `is_admin` account from spec 055, and the view is part of that dashboard.
- The exact license text is the one the user gave. It gets a Spanish translation under the default-Spanish rule (spec 063).
- Getting licenses, contacting sites, and any special handling for licensed sites are out of scope. The record only supports the decision.
- No per-domain allow or deny list is added. Each capture still tries the site every time.
- Distinct members can be counted with a one-way, salted fingerprint per domain, which is not reversible to an account. The exact method is left to planning.
