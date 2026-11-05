# Feature Specification: Capture a Recipe from a URL

**Feature Branch**: `worktree-26`

**Created**: 2026-11-04

**Status**: Draft

**Input**: User description: "@dev/docs/backlog.yaml 026 @prd". Backlog S-026, "Capture a recipe from a URL (SSRF-safe fetch, JSON-LD first)", journey J2, acceptance AC2.3. PRD `dev/docs/prd.md` §1.5A, §1.7 (error mapping, URL fetching), §1.10 (add-recipe call to action), §2 J2, §4 (no crawling, imported recipes keep their source link), Appendix B.1. Builds on text capture (spec 016), its error messages (spec 017), catalog matching (spec 018), custom units (spec 055), save (spec 020), the recipe detail source link (spec 027 FR-003) and the account language (spec 063).

## Clarifications

### Session 2026-11-04

- Q: When a link opens fine but the page has no recipe on it, which message should the member see? → A: A new message, "We couldn't find a recipe on that page. Paste the recipe text instead." The page message ("We couldn't open that page…") stays for pages that cannot be opened. This refines PRD J2 ("The URL has no recipe → PageFetchFailed").
- Q: When a recipe page shows a photo of the dish, should the saved recipe keep that photo as its preview image? → A: Yes. The app fetches the page's main recipe photo too, with the same address checks and a size limit, and stores it as the recipe's preview image. This is one extra request beside the page and amends PRD §4 ("fetches exactly the one page").
- Q: Should a link that names a port other than the normal web ports be refused? → A: Yes. Only ports 80 and 443 are allowed, for the page, every redirect and the photo; any other port is refused with the page message.
- Q: Should the app open pages the way a browser does (running the page's scripts) to capture sites that build their content only in the browser? → A: Not now. This story reads the HTML as the site sends it; rendering pages is a later backlog story (S-066), which would need an architecture exception.
- (owner, 2026-11-04, after Q5) Markdown still over the limit after cleanup is split into batches, read at the same time and merged (FR-013a). The recipe reader gets a partial page mode for these batches, so a batch may hold only part of a recipe (FR-013b).
- Q: When a page's text is longer than what the app sends to the assistant, should the app cut it or refuse the page? → A: Clean the page first: turn its main content from HTML into Markdown, keeping headings, lists, numbered steps and tables and dropping scripts, styles, navigation, ads, comments and hidden elements, so more useful detail fits. If the Markdown is still over the limit, it is split into batches that are read separately and merged into one draft (FR-013a); only Markdown beyond the batch cap is cut, with a note on the draft.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Turn a recipe page link into a reviewable draft (Priority: P1)

A member found a recipe on a website. In a notebook (their own, or one of a kitchen's), they tap the add-recipe call to action, choose **URL**, paste the link and submit. After a short wait they see the same draft review screen as text capture: title, base servings, ingredient lines and steps, all editable, with the catalog matches of spec 018 and the unit questions of spec 055. When the page describes the recipe in the structured format that recipe websites publish for search engines (schema.org Recipe), the title and steps come from that description. They review it and save it; the saved recipe keeps a link to the page.

**Why this priority**: It is the whole feature. Most of the couple's recipes outside cookbooks are on websites, and copying the text by hand is the friction this removes.

**Independent Test**: With a saved copy of a recipe page that carries schema.org Recipe data, submit its link and check that the draft's title and steps match that data (AC2.3), that the draft can be saved, and that the saved recipe shows a link to the page.

**Acceptance Scenarios**:

1. **Given** a page with schema.org Recipe data, **When** the member submits its link, **Then** a draft opens whose title and steps come from that data (AC2.3), and whose ingredient lines follow the same rules as text capture (singular lower-case names, preparation apart, vague amounts, allowed units, sizes).
2. **Given** a page with schema.org Recipe data that states the servings as a number, **When** the draft opens, **Then** base servings are that number with no "estimated" badge.
3. **Given** a recipe page with no schema.org Recipe data, **When** the member submits its link, **Then** the draft is built from the page's main content turned into Markdown (FR-012), as text capture would build it from pasted text.
4. **Given** a page whose schema.org Recipe data has no ingredients, **When** the member submits its link, **Then** the draft is built from the page's main content as Markdown instead (PRD J2).
5. **Given** a recipe page that names a main recipe photo, **When** the draft opens, **Then** it shows that photo as the preview image, and the member can remove it before saving; **When** the member saves, **Then** the recipe keeps the photo as its preview image.
6. **Given** a draft from a link, **When** the member saves it, **Then** the recipe is saved into the capture's notebook as in spec 020, and its detail shows a link to the page (spec 027 FR-003).
7. **Given** a draft from a link, **When** the member presses Back, **Then** they return to the link sheet with the link unchanged; **When** they press Discard, **Then** they return to an empty link sheet and nothing is saved.

---

### User Story 2 - Get a clear message when the page cannot be used (Priority: P2)

The link is wrong, the site is down or refuses the app, the page is not a web page (a PDF or an image), it is too large, or it holds no recipe. The member sees one plain message that tells them what to do next, and the link stays in the field.

**Why this priority**: Websites fail often (paywalls, sign-in walls, pages built only in the browser). Without a clear way out, the member is stuck; the message points them to pasting the text instead, which already works.

**Independent Test**: Submit links to an address that does not answer, a page that returns an error, a PDF, a page over the size limit and a page with no recipe; each shows the page message and keeps the link.

**Acceptance Scenarios**:

1. **Given** a link the app cannot open (no answer within 10 seconds, an error status, more than 3 redirects, not a web page, larger than 2 MB), **When** the member submits it, **Then** they see "We couldn't open that page. Paste the recipe text instead." and the link stays in the field.
2. **Given** a page that opens but holds no recipe, **When** the member submits it, **Then** they see "We couldn't find a recipe on that page. Paste the recipe text instead.", the link stays in the field, and nothing is created.
3. **Given** a page that holds two or more complete recipes, **When** the member submits it, **Then** they see "Upload only one recipe at a time" and nothing is created.
4. **Given** the assistant fails (no answer in time, usage limit, unreadable answer, not set up), **When** the member submits a link, **Then** they see the matching message from spec 016 and spec 017, worded for a link ("Your link is kept"), and the link stays in the field.
5. **Given** the member's account language is Spanish, **When** any of these messages appears, **Then** it is in Spanish.

---

### User Story 3 - The app never reaches inside its own network (Priority: P1)

Whatever a member pastes, the app opens only public web pages. A link to the app's own server, the home network, a private address, or a cloud metadata address is refused, also when a public page redirects there.

**Why this priority**: Fetching a link the user chose is the one place where a member can make the server send a request. Without these rules, a link could read internal services. It is a security requirement and cannot be cut.

**Independent Test**: Submit links that point (directly, by a name that resolves there, or through a redirect) at loopback, private, link-local and metadata addresses, and at non-web schemes; every one is refused with the page message and no request reaches the target.

**Acceptance Scenarios**:

1. **Given** a link that is not `http` or `https` (for example `file:`, `ftp:`, `javascript:`), **When** submitted, **Then** it is refused before any request is made.
2. **Given** a link whose host is, or resolves to, a loopback, private, link-local, unspecified or cloud metadata address (IPv4 or IPv6), **When** submitted, **Then** it is refused before any request is made.
3. **Given** a public page that redirects to such an address, **When** submitted, **Then** the redirect is not followed and the page message is shown.
4. **Given** a page with text that tries to give the assistant instructions (for example "ignore previous instructions"), **When** submitted, **Then** the draft is built as for any page and the text has no effect on how it is built.

---

### Edge Cases

- The field is empty or holds only spaces: the submit control is disabled.
- The field holds text that is not a link (no scheme and no host, or spaces inside): the submit control is disabled and the member sees "Paste a link that starts with http:// or https://". A link pasted without a scheme ("example.com/soup") is read as `https://`.
- A link longer than 2,048 characters: the submit control is disabled and the member sees "That link is too long."
- A link with a user name or password in it (`https://user:pass@host/…`), or on a port other than 80 or 443 (`https://host:8080/…`), directly or through a redirect: refused with the page message.
- The page is built only in the browser and its HTML holds neither recipe data nor recipe text: the page holds no recipe, so the no-recipe message (FR-021a) is shown. The app does not run the page's scripts.
- The page needs a sign-in or is behind a paywall : a status 401, 402 or 403 shows the page message; a sign-in page that opens with no recipe on it shows the no-recipe message (FR-021a).
- The schema.org data holds several Recipe items: the capture is refused with "Upload only one recipe at a time".
- The schema.org data states servings as text without a number ("serves a crowd"): base servings are estimated and flagged, as in text capture.
- The schema.org steps are grouped into sections: the steps are taken in page order, as one list.
- The page's Markdown is longer than the assistant input limit: it is split into batches, read at the same time and merged into one draft (FR-013a). The member sees one draft, as for a short page.
- The page's Markdown is longer than all batches together can hold: the part beyond the last batch is not read, and the draft shows "This page was long, so part of it was not read. Check the ingredients and steps." The member can add what is missing by hand.
- The ingredients are in one batch and the steps in another: the merged draft has both; the missing-part rules of spec 017 are checked on the merged draft only.
- The same ingredient list appears twice on the page (for example in the article and again in a printable card): identical lines are kept once.
- One batch fails (no answer in time, usage limit, unreadable answer): the whole capture fails with that message, as for one call; the link stays in the field.
- The page is long only because of comments, menus or ads: these are dropped before the limit is applied (FR-012), so the recipe itself is not cut.
- The same link was captured before into the same notebook: the capture works again and a second recipe is saved if the member saves it. There is no duplicate check.
- The page has a recipe photo: it is fetched and shown on the draft (FR-005a). When the photo is missing, blocked, too large, not an image, or not ready in time, the draft opens without one and no message is shown; the photo never makes a capture fail.
- The page names several photos: only the first one in the schema.org Recipe data is used, or, with no schema.org photo, the page's main share image.
- The kitchen is archived while the link sheet is open: submitting is refused with the archived-kitchen message from spec 016 FR-033, before any page is fetched, and the link stays in the field.
- The member is removed from the kitchen while the link sheet is open: submitting is refused as not found, before any page is fetched, and the link stays in the field.
- The member reloads or leaves an edited draft by another route than Back or Discard: they are asked first, as in spec 016 FR-032.

## Requirements *(mandatory)*

### Functional Requirements

**Entry and input**

- **FR-001**: The URL option of the add-recipe options dialog (PRD §1.10) MUST be enabled and MUST open a link sheet with one link field and a submit control. No other entry point is added; the option list stays in the shared add-recipe component. Picture stays disabled until S-041.
- **FR-002**: A capture from a link MUST be for exactly one notebook, chosen exactly as for text capture (spec 016 FR-001a, spec 056 capture step). Notebook access rules (spec 016 FR-022, FR-030) and the archived-kitchen rule (spec 016 FR-033) apply unchanged and MUST be checked before the page is fetched.
- **FR-003**: The submit control MUST be disabled while the field is empty, holds only spaces, is not a link, or is longer than 2,048 characters, with the messages listed under Edge Cases. A link with no scheme MUST be read as `https://`.
- **FR-004**: While the page is being opened and read, the system MUST show the shared progress state and MUST NOT accept a second submission until the first one ends. One attempt per submission; no automatic retry (spec 016 FR-025).

**Fetching the page**

- **FR-005**: The system MUST fetch the one page the member gave and, at most, its one main recipe photo (FR-005a), and nothing else: no other pages of the site, no other images, no scripts and no style sheets (PRD §4, no crawling, amended by Clarifications 2026-11-04). It MUST NOT run the page's scripts.
- **FR-005a**: When the page names a main recipe photo (the first image of the schema.org Recipe item, or else the page's main share image), the system MUST fetch it under the same rules as the page (FR-006 to FR-008 and FR-010), MUST accept only JPEG, PNG or WebP images up to 2 MB, and MUST give up on it after 5 seconds. The photo MUST be fetched while the recipe is being read, so it does not add to the member's wait beyond SC-002. Any failure leaves the draft without a photo and shows no message.
- **FR-006**: The system MUST accept only `http` and `https` links on port 80 or 443 (stated or implied by the scheme), and MUST refuse a link on any other port or with a user name or password in it.
- **FR-007**: Before each request, including each redirect, the system MUST resolve the host and MUST refuse the request when any resolved address is loopback, private, link-local, unspecified, multicast, reserved, or a cloud metadata address, for IPv4 and IPv6 (including IPv4 addresses written inside IPv6). The request MUST go to the address that was checked, so the name cannot resolve to a different address between the check and the request.
- **FR-008**: The system MUST follow at most 3 redirects, and MUST check each new address under FR-006 and FR-007.
- **FR-009**: The system MUST stop and refuse the page when it has not finished within 10 seconds in total, when it is larger than 2 MB (stopping the download once the limit is passed, whatever size the site announces), when its status is not a success, or when it is not an HTML page.
- **FR-010**: The fetch MUST identify itself with a fixed, generic client name and MUST NOT send the member's cookies, session, email or any other personal data to the site.

**Reading the recipe**

- **FR-011**: When the page holds exactly one schema.org Recipe item with at least one ingredient, the system MUST take the title and the steps from it, and the servings when they are given as a number. The ingredient lines MUST still be read by the recipe-extraction assistant, with the notebook's catalog, under the same rules as text capture (PRD §1.5A, Appendix B.1), so that names, quantities, units, sizes, preparations and vague amounts follow those rules.
- **FR-012**: When the page has no schema.org Recipe item, or its Recipe item has no ingredients, the system MUST build the draft from the page's main content turned from HTML into Markdown, sent to the assistant inside the same data block as pasted text. The Markdown MUST keep headings, lists, numbered steps, tables and paragraph breaks, and MUST drop scripts, styles, navigation, headers and footers, ads, comment sections, forms, hidden elements and images. Links keep their text only.
- **FR-013**: Each request to the assistant MUST hold at most a configured number of characters of Markdown (the batch limit), and a capture MUST use at most a configured number of batches (the batch cap). Both are kept in settings, not in code. Markdown beyond the batch cap MUST NOT be read, and the draft MUST then show "This page was long, so part of it was not read. Check the ingredients and steps." in the member's language.
- **FR-013a**: When the Markdown is longer than the batch limit, the system MUST split it into batches in page order, only between blocks (headings, paragraphs, list items, table rows), never inside a line. The batches MUST be sent to the assistant at the same time, each with the notebook's catalog and marked as one part of a single page that may hold only part of a recipe. Each batch is one attempt with no retry (spec 016 FR-025). The results MUST be merged into one draft:
  - the title from the first batch that gives one, and the servings from the first batch that states them (otherwise estimated, as in text capture);
  - ingredient lines and steps joined in page order, with identical lines (same name, amount, unit, size and preparation) kept once;
  - the draft rules and the missing-part messages of spec 017 checked on the merged draft, not on each batch;
  - the no-recipe message (FR-021a) only when no batch finds any part of a recipe;
  - "Upload only one recipe at a time" when any batch reports two complete recipes, or two batches each give a complete recipe with a different title;
  - when any batch fails, the whole capture fails with that batch's message (FR-022), and no partial draft is shown.
- **FR-013b**: The recipe reader MUST have a partial page mode, used only for batches. In it, a batch MAY return a recipe part with any of title, servings, ingredient lines and steps missing, and MUST NOT be refused for a missing part; a batch with no recipe content returns "no recipe here". The whole-recipe mode used by text capture and by single-batch pages is unchanged.
- **FR-014**: The page's content, its schema.org data included, MUST be treated as data and never as instructions (PRD §1.7, Prompt injection): text in the page that tries to change the assistant's behaviour MUST NOT change how the draft is built.
- **FR-015**: Steps taken from schema.org data MUST keep the page's order, MUST be flattened out of any sections into one list, and MUST be plain text (no markup).
- **FR-016**: When the schema.org data holds two or more Recipe items, or the assistant reports two or more complete recipes in the page's Markdown, the capture MUST be refused with "Upload only one recipe at a time" and nothing created.

**Draft and save**

- **FR-017**: A valid result MUST open the draft review screen of spec 016, with catalog matching (spec 018) and unit questions (spec 055) as for text. Every draft rule and edit control of spec 016 applies unchanged.
- **FR-018**: Back on the draft MUST return to the link sheet with the link unchanged; Discard MUST return to an empty link sheet; neither saves anything.
- **FR-019**: Capturing, editing and discarding a draft from a link MUST NOT create any record. Save (spec 020) MUST store the recipe's source with type "url" and the final page address after redirects, and MUST NOT store the page's HTML or text. When the draft still has its photo at save, the photo MUST be stored as the recipe's preview image (PRD §1.6, `preview_image_base64`), reduced to a preview size set in the plan; it MUST be shown from the stored copy, never loaded from the site. Before save the member MUST be able to remove the photo from the draft.
- **FR-020**: The saved recipe's detail MUST show the link to its page (spec 027 FR-003).

**Errors**

- **FR-021**: A page that cannot be opened (FR-006 to FR-009) MUST show "We couldn't open that page. Paste the recipe text instead." (PRD §1.7) and MUST NOT show a draft or create data.
- **FR-021a**: A page that opens but holds no recipe (no schema.org Recipe item with ingredients, and the assistant reports the page's Markdown is not a recipe) MUST show "We couldn't find a recipe on that page. Paste the recipe text instead." in place of the not-a-recipe message of spec 017, and MUST NOT show a draft or create data.
- **FR-022**: The assistant failure messages of spec 016 (FR-016, FR-017, FR-018, FR-028) and the missing-part messages of spec 017 MUST be shown for a link capture too, with "Your text is kept" worded as "Your link is kept" where it appears.
- **FR-023**: After every refused or failed capture, the link MUST stay in the field unchanged.
- **FR-024**: No message MAY contain raw service errors, site error pages, resolved addresses, keys or technical traces. (Spec 067 adds `site_requires_license` for a site's own 401/402/403/451 refusal; its message holds none of these either.)
- **FR-025**: Every text of this feature (link sheet, buttons, messages) MUST exist in English and Spanish and follow the account language (spec 063).

**Other channels**

- **FR-026**: The link capture MUST be built so the MCP capture tool (S-032) can reuse it with the same rules; the MCP tool itself is not part of this feature.

### Key Entities

- **Link capture**: one submission of one page address for one notebook. It holds the address the member gave, the final address after redirects, and either a draft or a refusal. Nothing of it is stored unless the draft is saved.
- **Source**: where a saved recipe came from (PRD §1.6). For this feature: type "url" and the final page address. Deleted with the recipe (spec 027).
- **Recipe draft**: as in spec 016; built here from schema.org data plus the assistant, or from the page's Markdown plus the assistant, in one batch or merged from several; it notes when Markdown beyond the batch cap was not read.
- **Batch**: one block-aligned piece of a page's Markdown, sent in its own assistant request. Exists only while the capture runs; never stored. May carry one preview photo taken from the page.
- **Recipe preview image**: the stored, reduced copy of the page's main photo, kept on the recipe (PRD §1.6). Deleted with the recipe.
- **Notebook** and **ingredient catalog**: as in specs 056 and 018; the catalog of the capture's notebook is sent with the ingredient lines.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For each saved recipe page in the evaluation set that carries schema.org Recipe data, the draft's title and steps equal that data, in 100% of runs (AC2.3).
- **SC-002**: After submitting a link, the member sees a draft or a message within 22 seconds (10 seconds for the page, the assistant's text wait, and 2 seconds), in 100% of runs with default settings, also when the page is read in several batches (they run at the same time).
- **SC-009**: For a long evaluation page whose ingredients and steps fall in different batches, the merged draft has every ingredient line and step of the expected draft, in page order and with no duplicated lines, in 100% of runs with the fake assistant.
- **SC-003**: Every link in the blocked-address test set (loopback, private, link-local, unspecified and metadata addresses, IPv4 and IPv6, given directly, by a name that resolves there, or through a redirect) is refused, and no request reaches the blocked address, in 100% of automated runs.
- **SC-004**: In every refused or failed capture, the link is still in the field, in 100% of runs.
- **SC-005**: No capture, edit or discard from a link creates a recipe, source, ingredient or step record, in 100% of automated runs; a saved one has a source of type "url" with the page address and no page content, and a preview image only when the draft had one at save.
- **SC-008**: A blocked photo address (as in SC-003) is never requested, and a photo that fails for any reason never stops a draft from opening, in 100% of automated runs.
- **SC-006**: Across the evaluation pages (at least 5 recipe pages from different sites, in English and Spanish, with and without schema.org data, plus one page with no recipe), at least 90% of drafts have the correct title, servings and ingredient lines when compared with the expected draft.
- **SC-007**: Each of the two household members captures a recipe from a link on the first attempt without help, in a short usability check.

## Assumptions

- **Page with no recipe**: PRD §2 J2 maps "The URL has no recipe" to PageFetchFailed. This spec keeps that error family but gives it its own wording (FR-021a, Clarifications 2026-11-04); the PRD §1.7 table gains this line when the story is done.
- **Recipe photo**: the page's main photo is fetched as one extra request (Clarifications 2026-11-04). PRD §4 "No crawling" is amended to "the page and its one main recipe photo" when the story is done. Storing it is allowed since the MVP rule on photos was lifted (constitution 2.0.0, PRD §4, 2026-11-04). Uploading or replacing a recipe image by hand is S-067.
- **No page rendering**: pages are read as the site sends them, without running scripts. Sites that build the recipe only in the browser and do not publish schema.org data cannot be captured; the member pastes the text instead. Rendering is deferred to backlog S-066 (Clarifications 2026-11-04).
- **Only standard web ports**: links that name a port other than 80 or 443 are refused (FR-006, Clarifications 2026-11-04). This goes beyond the PRD §1.7 list, which gains this line when the story is done.
- **Batch limit and batch cap**: two new settings, beside `RECIPE_TEXT_MAX_CHARS`: the characters of Markdown per assistant request and the most batches per capture. Defaults are decided in the plan. The member's paste limit does not apply to the link.
- **Batches and the assistant's usage limit**: each batch is one assistant request and counts against the shared usage limit; a long page uses up to the batch cap in requests. There is still no per-member limit.
- **Fetch timeout and size**: 10 seconds and 2 MB, as in PRD §1.7. The assistant's wait is `GEMINI_TEXT_TIMEOUT_S`, as for text.
- **Language**: names and steps follow the page's language, as text capture follows the pasted text. The kitchen's content_language is not used.
- **Fixtures**: tests use saved copies of invented recipe pages and a fake page fetcher; no test opens a real website. The evaluation set (S-034) adds the saved pages.

## Out of Scope

- Capturing from a photo (S-041) and the MCP capture tool (S-032).
- Fetching other pages or images other than the one main photo.
- Running page scripts or rendering pages in a browser (later, S-066).
- Duplicate detection for a link already captured.
- Showing the page's author, publisher or rating.
- Main ingredients and cuisines (S-061).
