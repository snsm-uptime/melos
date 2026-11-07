# Feature Specification: Acrylic App Chrome and the Portfolio Palette

**Feature Branch**: `072-acrylic-nav-palette`

**Created**: 2026-11-06

**Status**: Draft

**Input**: User description: "I want to copy the acrylic transparency of the nav from this website: [screenshot of the owner's portfolio, scrolled, with page content blurred under the nav]. Those styles belong to another repo of mine I have locally at /home/snsm/source/personal/portfolio or remote at https://github.com/snsm-uptime/portfolio. Copy the color palette and apply it for dark and light themes."

**Backlog story**: S-072 (owner request 2026-11-06, post-MVP; not in `dev/docs/prd.md`).

## Reference *(what is being copied)*

The owner's portfolio site (`snsm-uptime/portfolio`) is the source for both parts of this story.

**The acrylic nav.** At the top of the page the nav has no background of its own. Once the visitor scrolls, the nav gets the page background colour at about 80% opacity, the content passing under it is blurred, and a small shadow separates it from the page. The change fades in over about 300 ms.

**The palette.** The portfolio has one palette, a dark one (its light and dark definitions are identical):

| Role | Value | Notes |
|------|-------|-------|
| Page background | `#141218` | near-black with a violet cast |
| Surface (cards, panels, menus) | `#201d27` | |
| Text | `#e5e7eb` | |
| Quiet text | `#9ca3af` | |
| Primary brand | `#6d1aad` | violet; white text on it |
| Secondary brand | `#d82591` | magenta; white text on it |
| Accent | `#fd9c21` | orange; dark text on it |
| Destructive | `#ef4444` | red |
| Focus ring | `#6d1aad` at 50% | |

Because the portfolio has no light palette, Melos's light theme is **derived** from these colours (see FR-010 to FR-012).

## Clarifications

### Session 2026-11-06

- Q: Since the portfolio has no light palette, what should Melos's light theme look like? → A: A derived light theme: a pale background with a faint violet tint (about `#f7f5fa`), white cards and menus, dark violet-grey text, and the same violet, magenta and orange, deepened only where needed for contrast.
- Q: Which colour should mark Melos's main actions and selections (primary buttons, selected cards and rows, links, the "in cart" state, focus rings)? → A: Orange `#fd9c21` is the main colour (links, icons, selected cards and rows, the "in cart" state, hover, focus rings); violet `#6d1aad` is kept for the brand and for filled buttons, with white text.
- Q: Besides the top bars, which other surfaces should get the frosted see-through look? → A: The dots menus and the other dropdowns (always frosted while open). Top bars are frosted only where they are sticky and only once content has scrolled under them, so the change shows the member that the bar stays put.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - The top bar turns to frosted glass as the page scrolls (Priority: P1)

A member opens any page with a top bar (a notebook, a kitchen, a recipe, the cart, settings) and scrolls down. The bar stays in place; the content now slides under it, and the member sees it through the bar, blurred and dimmed, as on the portfolio site. Back at the top, the bar blends into the page again with no visible background or shadow. The title, back arrow and icon buttons in the bar stay sharp and readable throughout.

**Why this priority**: This is the visual effect the owner asked for first, and it is visible on every screen.

**Independent Test**: On the current colours, open a long notebook, scroll down and back up; check the bar against the portfolio's nav in both themes. Delivers the effect without the new palette.

**Acceptance Scenarios**:

1. **Given** a page scrolled to the very top, **When** it is shown, **Then** the top bar has no background, border or shadow of its own and looks like part of the page.
2. **Given** a page with more content than fits on screen, **When** the member scrolls down even a little, **Then** within about 300 ms the bar fades to the page colour at about 80% opacity, the content under it is visibly blurred, and a small shadow appears under the bar.
3. **Given** the bar in its frosted state, **When** the member scrolls back to the top, **Then** it fades back to transparent.
4. **Given** the frosted bar over any content (a photo, a coloured chip, text), **When** the member reads the title or uses a button in the bar, **Then** the text and icons are as readable as on a plain background (FR-006).
5. **Given** a recipe page on a phone, where its own header (Back, the cart, the source link and the dots menu) sticks to the top, **When** the member scrolls, **Then** that header behaves the same as the app's top bar.
6. **Given** a phone, **When** the member scrolls a page, **Then** the bar keeps clear of the notch and status bar exactly as it does today, and the frosted area fills the space behind them.
7. **Given** any page, **When** the member opens a dots menu or a dropdown list, **Then** the open list is frosted (FR-017): what lies beneath shows through blurred, and its items stay readable.

---

### User Story 2 - Melos wears the portfolio's colours in the dark theme (Priority: P2)

A member who uses the dark theme sees the portfolio's colours across the whole app: the near-black violet background, the slightly lighter surfaces for cards, menus and dialogs, light grey text, and the violet on filled buttons and the brand, orange on links, icons, selected items, the "in cart" state and focus rings, and magenta where Melos already uses its second brand colour. Nothing is left in the old warm brown and green.

**Why this priority**: The palette is the second half of the request; dark is the theme the portfolio actually defines, so it can be copied nearly as is.

**Independent Test**: Switch to dark and walk the main screens (sign-in, notebooks, a notebook, a recipe, the recipe editor, a kitchen, the cart and shopping list, settings, a dialog, a dots menu, a toast). Every screen uses only the new colours and every text passes the contrast check.

**Acceptance Scenarios**:

1. **Given** the dark theme, **When** any screen is shown, **Then** its background, surfaces, text, borders, primary actions, selected states and focus rings use the dark palette (FR-008).
2. **Given** a filled button, **When** it is shown, **Then** it is violet with white text; **Given** a link, a selected card or a focused control, **When** it is shown, **Then** it is marked in orange and meets the contrast rule (FR-013).
3. **Given** an error, a warning or a success message, **When** it is shown, **Then** it is still red, amber or green and still tells the member what it means; only its shade changes to sit on the new background.

---

### User Story 3 - A light theme in the same family (Priority: P3)

A member who uses the light theme (or whose device is set to light, with "system") sees a light version of the same brand: a pale background with a faint violet cast, white or near-white surfaces, dark text, and the same violet, magenta and orange as the dark theme. The two themes are clearly the same app.

**Why this priority**: The owner asked for both themes, but the portfolio has no light palette to copy, so this part is designed rather than copied and follows the dark one.

**Independent Test**: Switch to light and walk the same screens as story 2; switch back and forth between light, dark and system.

**Acceptance Scenarios**:

1. **Given** the light theme, **When** any screen is shown, **Then** it uses the light palette (FR-010), with the same brand colours as dark, adjusted only where needed to meet the contrast rule.
2. **Given** the frosted top bar in the light theme, **When** content scrolls under it, **Then** the bar shows the light page colour at about 80% opacity with blur and a shadow, as in dark.
3. **Given** the theme set to "system", **When** the device switches between light and dark, **Then** Melos follows it, with no page reload and no flash of the other theme or of the old colours when a page first loads.

---

### Edge Cases

- **Short pages.** A page that fits on screen never scrolls, so its bar stays transparent.
- **Pages that scroll inside a panel.** On wide screens some pages (a recipe's ingredients and steps) scroll inside columns, not the whole page. The bar turns frosted when the page's main content has scrolled; if nothing scrolls under the bar, it stays transparent.
- **Browsers that cannot blur.** The bar falls back to the page colour at near-full opacity, so text under it never shows through sharp and clashes with the bar's own text.
- **"Reduce transparency" set on the device.** The bar is solid (no see-through, no blur) when frosted.
- **"Reduce motion" set on the device.** The bar switches between transparent and frosted without the fade.
- **Bars with a progress bar** (capture steps). The progress bar stays at the very top and is part of the frosted area.
- **Bars that do not stick.** A top bar that scrolls away with the page (for example the recipe header on wide screens, where the page itself does not scroll) never turns frosted.
- **A menu or dropdown opened over a busy area** (a recipe photo, coloured chips) or over a frosted top bar is frosted too; its text stays readable (FR-019).
- **Dialogs, sheets, toasts and the side panel** keep their solid surfaces; they are not see-through.
- **The side panel.** On wide screens it is a fixed column that content never passes under, so it does not become frosted; on phones the drawer slides over the page and keeps a solid surface. It takes the new palette.
- **Signed-out screens** (sign-in, sign-up, password reset) take the new palette; those without a top bar have nothing to frost.
- **Images in recipes and avatars** are the member's own content and are not tinted.
- **Printing and the recipe PDF** are out of scope; they keep their current look.

## Requirements *(mandatory)*

### Functional Requirements

**Acrylic top bar**

- **FR-001**: Every sticky top bar in the app MUST behave as described here: the app's shared top bar, and the headers that recipe pages draw themselves (recipe, recipe edit, capture draft review) wherever they stay fixed while the content scrolls. The frosted look is the sign that the bar is sticky: a bar that scrolls away with the page MUST NOT become frosted.
- **FR-002**: While the page's main content is scrolled to its top, a top bar MUST have no background, border or shadow of its own.
- **FR-003**: Once the main content has scrolled under a sticky top bar by any amount, the bar MUST show the current theme's page background at about 80% opacity, MUST blur whatever passes beneath it, and MUST cast a small shadow on the content below. The change MUST fade over about 300 ms each way.
- **FR-004**: The main content MUST scroll beneath the top bar, so that the content is actually visible through it. The content MUST still start below the bar when at the top, so nothing is hidden behind the bar before the member scrolls.
- **FR-005**: The top bar MUST keep its current position, height, safe-area insets (notch, status bar) and contents. Only its background, blur and shadow change.
- **FR-006**: Text and icons in a frosted bar MUST meet the contrast rule (FR-013) against the bar laid over the darkest and the lightest content that can pass beneath it.
- **FR-007**: Where the device cannot blur, or asks for reduced transparency, the frosted bar MUST be solid instead. Where the device asks for reduced motion, it MUST switch without the fade.

**Acrylic menus and dropdowns**

- **FR-017**: Every dots menu and every dropdown list (the shared popup menu, the searchable pickers and the select lists) MUST be frosted while open: the theme's surface colour at about 80% opacity, a blur of whatever lies beneath it, and its current border and shadow. It has no transparent state.
- **FR-018**: Hovered, focused and selected items in a frosted menu MUST stay clearly marked (FR-012) against the frosted surface.
- **FR-019**: Item text and icons in a frosted menu MUST meet the contrast rule (FR-013) against the menu laid over the darkest and the lightest content that can lie beneath it; if 80% opacity cannot meet it, the menu MUST use a higher opacity rather than fail. The same solid fallback as FR-007 applies.

**Palette**

- **FR-008**: The dark theme MUST use the portfolio's palette for every colour role Melos has: page background `#141218`, surfaces `#201d27`, text `#e5e7eb`, quiet text `#9ca3af`, main colour orange `#fd9c21`, brand and filled-button violet `#6d1aad`, second brand magenta `#d82591`, error `#ef4444`, and focus rings in orange (FR-012). Values MAY be lightened or darkened only as far as needed to meet FR-013, and each such change MUST be listed with its reason in the plan.
- **FR-009**: Roles the portfolio does not define (borders and dividers, hovered and selected rows, selected cards, warning, success, disabled) MUST be derived from the palette's own colours, so no colour from the old warm palette remains.
- **FR-010**: The light theme MUST use a pale page background with a faint violet tint (about `#f7f5fa`), white surfaces for cards, menus and dialogs, dark text in the violet-grey family of `#141218`, and the same three brand colours as dark. It MUST NOT keep Melos's current cream and green, and it MUST NOT reuse the dark palette.
- **FR-011**: Where a brand colour on the light background fails FR-013, the light theme MUST use a deeper shade of that colour for text and small marks, and keep the original for large filled areas where it passes. Orange text, icons and focus rings on the light background in particular MUST use a deeper orange (the portfolio's `#fd9c21` is about 2:1 on a pale background).
- **FR-012**: Orange (`#fd9c21`) MUST be Melos's main colour: links, coloured icons, selected cards and rows, hovered and selected menu items, the "in cart" state, the selected tab, and focus rings. Anything filled with orange MUST carry dark text (`#141218`). Violet (`#6d1aad`) MUST be used for the brand and for filled buttons (primary actions such as Save, Confirm and Add), with white text. Magenta MUST be used wherever Melos uses its second brand colour. Error stays red, warning stays amber, success stays green in both themes; warning MUST be told apart from the orange main colour by its shade and by its icon or wording, never by colour alone.
- **FR-013**: In both themes, normal text MUST have a contrast of at least 4.5:1 against what it sits on, large text and icons, borders of inputs, and focus rings at least 3:1.
- **FR-014**: The theme setting (light, dark, system) MUST keep working as it does now: the choice is saved to the account, "system" follows the device, and the right palette is shown from the first paint of every page with no flash of the other theme or of the old colours.
- **FR-015**: The new palette MUST reach every screen, including signed-out screens, dialogs, sheets, menus, toasts, chips, badges, the side panel, the loading animation, and the admin dashboard.

**Out of scope**

- **FR-016**: This story MUST NOT change the portfolio's fonts, logo or layout into Melos, the shape or size of any control, the recipe PDF, or member content such as recipe images.

### Key Entities

- **Theme palette**: the named colour roles (page background, surface, text, quiet text, border, main colour (orange) and the text on it, brand and filled-button colour (violet) and the text on it, second brand (magenta) and the text on it, error, warning, success, focus ring, hovered and selected rows), each with a light and a dark value.
- **Top bar state**: transparent (main content at its top, or the bar is not sticky) or frosted (sticky bar with content scrolled under it), per page.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: On every screen with a sticky top bar, scrolling down by any amount turns the bar frosted within 0.3 s, and scrolling back to the top turns it transparent within 0.3 s.
- **SC-002**: Side by side with the portfolio's scrolled nav, the owner judges the frosted bar in dark the same effect (see-through, blurred, about as dark, small shadow).
- **SC-007**: Every dots menu and dropdown in the walk of story 2 opens frosted in both themes, and its item text passes the contrast check over a recipe photo and over plain text.
- **SC-003**: 100% of the text and background pairs in the palette, in both themes, meet the contrast rule in FR-013, checked with a contrast tool and listed in the plan.
- **SC-004**: In a walk of the main screens listed in story 2, in both themes, no element shows a colour from the old warm palette.
- **SC-005**: Switching the theme in the account menu changes every visible colour without reloading the page, and loading any page with each of the three settings shows no flash of a different theme.
- **SC-006**: Scrolling a long notebook (100 recipes) with the frosted bar stays as smooth as it is today on a mid-range phone, with no visible stutter.

## Assumptions

- "The nav" means Melos's sticky top bars (FR-001); the owner added menus and dropdowns (FR-017). Dialogs, sheets, toasts, the side panel and the phone drawer get the new colours but stay solid.
- The frosted state copies the portfolio's: page colour at 80% opacity, a standard-strength blur, a small shadow, a 300 ms fade, transparent at the top. The owner can tune these numbers during the browser walk.
- "Copy the colour palette" means replacing Melos's warm brown and green palette in both themes, not adding a third theme or a choice between palettes.
- Melos's colour roles map onto the portfolio's as set in FR-012 (orange main, violet brand and filled buttons, magenta second brand). The exact value per role is settled in the plan.
- The portfolio's border colour (surface at 50%) is almost invisible on its background; Melos needs visible borders on inputs and cards, so borders are derived (FR-009).
- No account or server change is needed: the theme setting already exists.
- No new library is needed.
