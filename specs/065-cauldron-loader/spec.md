# Feature Specification: Cauldron Loader

**Feature Branch**: `065-cauldron-loader`

**Created**: 2026-10-30

**Status**: Draft

**Input**: User description: "I want to create a loading component that is an animation of the following SVG [image: a dark cauldron with a rim, two side handles and two feet, a pale drip running down from the rim, and two pale bubbles of different sizes above it], the idea is that while loading, the bubbles are coming out of the cauldron in a loop, the cauldron's bubbles should be accent color and the cauldron a shade of the background that constrasts enough. I also want the cauldron to tilt side to side in a configurable angle (using default 25 degrees -+). The animation needs to be smooth and looped."

## Clarifications

### Session 2026-10-30

- Q: Where should the new cauldron loader appear once it's built? → A: Build it and replace every loading state, including the pulsing placeholder and the small spinners inside buttons.
- Q: What colors should the cauldron use when it's inside a button filled with the accent color? → A: Two tones: the cauldron uses the button's text color, and the bubbles and drip a lighter or darker version of it.
- Q: When a wait is very short, should the loader appear right away or only after a brief delay? → A: Always show it right away, for any wait.
- Q: How much should the cauldron tilt when it's tiny, inside a button? → A: 10 degrees each way, kept as a separate configurable value: one default for buttons (10) and one for everywhere else (25).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - See that the app is working (Priority: P1)

A person waiting for something in Melos sees a small cauldron with bubbles rising out of it, over and over, so they know the app is busy and has not frozen.

**Why this priority**: This is the whole purpose of the feature. Bubbles rising in a loop is the smallest version that gives value.

**Independent Test**: Show the loader on its own for at least 30 seconds and watch that bubbles keep leaving the cauldron with no jump, stop or restart that the eye can catch.

**Acceptance Scenarios**:

1. **Given** something is loading, **When** the loader is shown, **Then** it shows the cauldron with its rim, two handles, two feet and drip, and at least two bubbles of different sizes.
2. **Given** the loader is showing, **When** time passes, **Then** bubbles rise out of the cauldron's mouth, fade away above it, and new ones follow.
3. **Given** the loader has been showing for several loops, **When** one loop ends and the next begins, **Then** the viewer cannot tell where the loop restarts.
4. **Given** the loader is showing, **When** the loading finishes and the screen removes it, **Then** it disappears with no leftover shapes.

---

### User Story 2 - Cauldron tilts side to side (Priority: P2)

While the bubbles rise, the cauldron rocks gently left and right, which gives the loader its character. Whoever places the loader can set how far it tilts; by default it goes 25 degrees each way, or 10 degrees inside a button.

**Why this priority**: It adds the personality the owner asked for, but the loader already does its job without it.

**Independent Test**: Show the loader with no tilt setting and check that it rocks to 25 degrees each side. Then set another angle and check that it rocks to that angle instead.

**Acceptance Scenarios**:

1. **Given** no tilt angle is set, **When** the loader is shown, **Then** the cauldron rocks between 25 degrees left and 25 degrees right of upright.
2. **Given** a tilt angle of 10 degrees is set, **When** the loader is shown, **Then** the cauldron rocks between 10 degrees left and 10 degrees right.
3. **Given** the cauldron is rocking, **When** it reaches the end of a swing, **Then** it slows down, turns and speeds up again, with no sudden change of direction.
4. **Given** a tilt angle of 0 is set, **When** the loader is shown, **Then** the cauldron stays upright and the bubbles keep rising.
5. **Given** no tilt angle is set and the loader is inside a button, **When** it is shown, **Then** the cauldron rocks between 10 degrees left and 10 degrees right.

---

### User Story 3 - Loader fits the light and dark themes (Priority: P2)

The loader looks like part of Melos in the light theme and in the dark theme: the bubbles use the app's accent color and the cauldron uses a shade of the page background that stands out clearly against it.

**Why this priority**: A cauldron that disappears into the page, or colors that belong to neither theme, would make the loader useless or out of place.

**Independent Test**: Show the loader in both themes, and switch theme while it runs. Measure the contrast of the cauldron against the background.

**Acceptance Scenarios**:

1. **Given** the light theme, **When** the loader is shown, **Then** the bubbles and drip use the accent color, and the cauldron is a shade of the background clearly visible against it.
2. **Given** the dark theme, **When** the loader is shown, **Then** the same holds with the dark theme's accent and background.
3. **Given** the loader is showing, **When** the person switches theme, **Then** its colors change to match, and the animation keeps running without restarting.

---

### User Story 4 - Loader works for people who cannot see or do not want motion (Priority: P3)

A person using a screen reader is told that something is loading, in their language. A person who has asked their device to reduce motion sees a still cauldron with its bubbles instead of an animation.

**Why this priority**: The loader must not exclude anyone, though it affects fewer people than the main experience.

**Independent Test**: Use a screen reader with the loader showing, in Spanish and in English. Then turn on the device's reduce-motion setting and check that nothing moves.

**Acceptance Scenarios**:

1. **Given** a screen reader, **When** the loader appears, **Then** a loading message is announced in the person's language, and the drawing itself is not described.
2. **Given** the device is set to reduce motion, **When** the loader is shown, **Then** it shows the still cauldron and bubbles, with no tilt and no rising.

---

### Edge Cases

- **Very short loads**: the loader shows right away with no delay, even if the load ends in a moment. When the load ends it is removed at once; a partly finished loop is simply dropped, not played out.
- **Very long loads**: the loop keeps running for as long as the load lasts, with no drift or change of speed.
- **Tilt angle outside the allowed range**: an angle above 45 degrees is treated as 45. A negative angle uses its size (−10 behaves as 10), because the rocking goes both ways anyway. A value that is not a number uses the default for that place: 10 in a button, 25 elsewhere.
- **Small spaces**: the tilted cauldron and the rising bubbles stay inside the loader's own area at every size, so they never get clipped or push nearby content around.
- **Several loaders on one screen**: each one runs without affecting the others.
- **Loader placed on a card instead of the page**: the cauldron stays visible on the app's surface color as well as on the background.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The app MUST provide one shared loading indicator, built from the supplied cauldron drawing: body, rim, two side handles, two feet, a drip from the rim, and bubbles of different sizes.
- **FR-002**: While shown, bubbles MUST rise repeatedly from the cauldron's mouth and fade away above it, with at least two bubbles of different sizes on the screen across each loop.
- **FR-003**: Bubbles MUST appear and disappear gradually; no bubble may pop into view or vanish suddenly.
- **FR-004**: The cauldron, including its drip, MUST rock side to side around upright, between the same angle to the left and to the right.
- **FR-005**: The app MUST keep two configurable default tilt angles, each kept in one place: 25 degrees each way for general use and 10 degrees each way for loaders inside buttons. Each place that uses the loader MAY set its own angle instead.
- **FR-006**: The accepted tilt angle MUST run from 0 to 45 degrees, handled as listed under Edge Cases when a value falls outside that.
- **FR-007**: The rocking MUST ease in and out at the end of each swing, with no sudden change of speed or direction.
- **FR-008**: The animation MUST loop with no stop, jump or visible seam, for as long as the loader is shown.
- **FR-009**: Outside buttons, the bubbles and drip MUST use the app's current accent color. Inside a button, the cauldron MUST use the button's text color, and the bubbles and drip a lighter or darker version of it.
- **FR-010**: Outside buttons, the cauldron MUST use a shade of the current background color with enough contrast to stand out (see SC-003), in the light theme and in the dark theme, and MUST follow a theme change while running.
- **FR-011**: The loader MUST tell assistive technology that something is loading, in the person's language (Spanish and English), and MUST allow the place using it to give a more specific message.
- **FR-012**: When the device is set to reduce motion, the loader MUST show a still cauldron with its bubbles and no movement.
- **FR-013**: The loader MUST scale to the size the place using it asks for, with all its motion staying inside its own area.
- **FR-014**: The loader MUST NOT depend on any network request, so it can show while the network is slow.
- **FR-015**: The loader MUST replace every existing loading state in the app, including the pulsing page placeholder and the small spinners inside buttons, and no other loading animation may remain.
- **FR-016**: The loader MUST appear as soon as a wait starts, with no delay and no minimum display time.

### Key Entities

- **Tilt angle**: how far, in degrees, the cauldron rocks to each side of upright. Range 0 to 45. Default 25 for general use and 10 inside buttons; both defaults are configurable, and a single use can set its own.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Watching the loader for 60 seconds, a viewer cannot point out where the loop restarts.
- **SC-002**: With no setting given, the cauldron reaches 25 degrees to each side (10 inside a button), within 1 degree; with a custom setting, it reaches that angle within 1 degree.
- **SC-003**: The cauldron has a contrast ratio of at least 3:1 against the background and against the surface color, in both themes. The bubbles and drip meet the same 3:1 against the background. Inside a button, the cauldron, bubbles and drip each reach 3:1 against the button's fill, in every button style and both themes.
- **SC-004**: During a recorded 30-second run on a typical phone, the animation shows no visible stutter or dropped motion, and the page stays as responsive as it is without the loader.
- **SC-005**: In both themes, in Spanish and in English, 100% of screen-reader checks announce a loading message.
- **SC-006**: With reduce motion on, nothing moves on the loader over a 30-second check.
- **SC-007**: A search of the app finds no loading animation other than the cauldron loader.

## Assumptions

- "Shade of the background" means a color derived from the theme's background, so it stays in step with the theme: darker than the background in the light theme, lighter in the dark theme.
- The drip keeps the bubbles' color, because they share one color in the supplied drawing, and it moves with the cauldron.
- Bubbles rise straight up the screen, whichever way the cauldron is leaning.
- The cauldron rocks around a point near its base, so it looks like it sits on the surface.
- The rocking and the bubbles run in one calm, unhurried loop, with the exact timing tuned by eye against FR-007 and FR-008.
- The loader is decorative apart from its loading message: it takes no tap or keyboard input.
- Progress is not shown: the loader says "still working", not how much is left.
- Reused: the existing accent, background and surface theme colors, and the app's Spanish and English text. No new library is expected.
