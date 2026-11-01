# Research: Cauldron Loader

No NEEDS CLARIFICATION remained. These are the design decisions.

## R1. How it is drawn and animated

- **Decision**: Inline SVG with CSS keyframes in an SCSS module. Only `transform` and `opacity` animate. No JavaScript timer, no animation library, no image file.
- **Rationale**: FR-014 (no network) and SC-004 (no stutter, page stays responsive). Transform and opacity run on the compositor, so the loop costs no layout or paint. The project already animates with CSS (`base-button-spin`, `tooltip-fade-in`).
- **Alternatives considered**: An animation library or Lottie, rejected because the spec expects no new library. A canvas or `requestAnimationFrame` loop, rejected because it runs script on every frame. SMIL inside the SVG, rejected because it cannot read the theme colours or the tilt prop.

## R2. Shape and layers

- **Decision**: Two groups in one SVG. The cauldron group holds body, rim, two handles, two feet and the drip, and rocks. The bubble group sits outside it and does not rock. No `id`, `clipPath` or gradient is used.
- **Rationale**: Spec assumption: bubbles rise straight up whichever way the cauldron leans, and the drip moves with the cauldron. With no ids, several loaders on one screen cannot clash.
- **Alternatives considered**: Bubbles inside the rotating group, rejected because they would rise at an angle. One `<img>` of the supplied SVG, rejected because it cannot take theme colours.
- **Note**: The supplied drawing is a picture, not a file in the repo. The geometry is redrawn from it by eye and lives in `geometry.ts`.

## R3. Tilt, pivot and staying inside the box

- **Decision**: The group rotates around a pivot near the base of the feet. The angle reaches the CSS as a custom property `--cauldron-tilt` (for example `25deg`) and the keyframes use `rotate(calc(var(--cauldron-tilt) * -1))` and `rotate(var(--cauldron-tilt))`. `geometry.ts` sets the `viewBox` so the cauldron rotated by 45 degrees (the largest allowed) still fits inside it, and a test rotates the cauldron's outline points by 45 degrees and checks them against the box.
- **Rationale**: FR-013 and the "small spaces" edge case: nothing is clipped or pushes content around. One box that fits the worst case keeps the loader's size constant at every angle. A prop that only sets a variable needs no new keyframes per angle.
- **Alternatives considered**: One `@keyframes` per angle, rejected because the angle is a free number. Scaling the cauldron down as the angle grows, rejected because the size would change with the setting.

## R4. A loop with no seam

- **Decision**: The rock keyframes run `-tilt` to `+tilt` to `-tilt` with `ease-in-out` on each half, so speed is zero at both ends (FR-007) and the last frame equals the first (FR-008). One period, about 3.2 s, is tuned by eye. Each bubble has the same period and its own phase set with a **negative** `animation-delay`, so bubbles are already mid-rise when the loader mounts. Each bubble fades in at the mouth, rises, and fades out at the top, with opacity 0 at both ends of its keyframes.
- **Rationale**: FR-016 forbids a delay before the loader shows, and FR-002 wants bubbles on screen across each loop. A positive delay would show an empty cauldron at first. Equal periods mean the whole picture repeats exactly once per period, so there is no beat between the rock and the bubbles (SC-001).
- **Alternatives considered**: Different periods for rock and bubbles, rejected because the combined pattern would only repeat after a long time and could look like a restart. Linear easing on the rock, rejected by FR-007.

## R5. Reduced motion

- **Decision**: The still pose is the default style: cauldron upright, bubbles at fixed visible positions at full opacity. The `animation` rules sit inside `@media (prefers-reduced-motion: no-preference)`.
- **Rationale**: FR-012 and SC-006. If the media query is unsupported or fails, the safe result is a still picture, not a moving one.
- **Alternatives considered**: `animation: none` inside `prefers-reduced-motion: reduce`. It is the usual form, but it leaves bubbles at their keyframe-0 opacity of 0 unless the base style is also the still pose, so it needs the same base style anyway and fails the other way round.

## R6. Colours, and the loading button

- **Decision**: Two tones.
  - **Page tone** (default): bubbles and drip `var(--accent)`. Cauldron `color-mix(in srgb, var(--background) 40%, var(--foreground))`.
  - **Button tone**: cauldron `var(--loader-ink)`, bubbles and drip `color-mix(in srgb, var(--loader-ink) 80%, var(--loader-fill))`. `--loader-ink` and `--loader-fill` are the button's text and fill, set per variant in `BaseButton.module.scss`. They default to `currentColor` and `var(--background)` for header icon buttons that have no fill.
- **Rationale**: Contrast measured from the tokens in `globals.css` (WCAG relative luminance):

  | Pair | Light | Dark |
  |---|---|---|
  | Accent on background | 5.58 | 8.45 |
  | Cauldron (40% background) on background | 4.03 | 6.08 |
  | Cauldron (40% background) on surface | 4.35 | 5.49 |
  | Primary button, bubble (80% text) on fill | 4.54 | 5.79 |

  The bubble share was first 70% of the text colour. The contrast test (T024) found a Ghost button in light at 2.97, under 3:1, so the share is 80%, which passes for every variant in both themes (Primary 4.54 and 5.79).

  All reach the 3:1 of SC-003 with room to spare. 40% is the lowest background share that keeps about 4:1 in light, where a 50% share is only 3.04 and too close to the line. The tokens are CSS variables, so a theme change recolours the loader and a running CSS animation does not restart (US3 scenario 3).
- **Finding that changes the button**: a button with `loading` is also `disabled`, and the disabled style paints grey text on a grey fill. Measured text on fill is **1.98** (light) and **2.16** (dark) for Primary, so the cauldron could not reach 3:1 in any variant that uses that look. The loading state therefore keeps the variant's normal fill and text and drops the lift and hover (still not clickable, `cursor: progress`). This is a visible change from today's grey loading button and is needed for SC-003.
- **Alternatives considered**: Keep the grey loading button and give the loader fixed colours, rejected because the spec says the cauldron uses the button's text colour. Mix toward black or white instead of toward the fill, rejected because "lighter or darker" then depends on the theme; mixing with the fill is one formula for every variant.

## R7. Tilt rule

- **Decision**: `resolveTilt(value, fallback)`: if `value` is a finite number, return `min(abs(value), 45)`; otherwise return `fallback`. Defaults `CAULDRON_TILT_DEFAULT = 25` and `CAULDRON_TILT_IN_BUTTON = 10` and the limit `CAULDRON_TILT_MAX = 45` are exported constants in `tilt.ts`. The fallback is picked by tone.
- **Rationale**: FR-005, FR-006 and the Edge Cases table, in one pure function that tests without a DOM. `NaN`, `undefined`, a string and `±Infinity` are "not a number" and take the fallback. `0` stays `0`.
- **Alternatives considered**: Reading the defaults from an environment variable, rejected because "configurable" in the spec means one place in the code, and the constitution keeps environment for secrets and models.

## R8. Size

- **Decision**: A `size` prop takes any CSS length. In page tone it sets the width (default `3rem`) and the height follows the `viewBox` ratio. In button tone it sets the **height** (default `1.2em`, the button's own line height) and the width follows the ratio.
- **Rationale**: FR-013 and no layout shift when a button flips to loading. If button tone set the width, a drawing taller than wide would be taller than the line and the button would grow. Fixing the height makes that impossible. The old spinner was `1em`.
- **Alternatives considered**: A fixed pixel size, rejected because buttons come in three font sizes.

## R9. Accessible message and language

- **Decision**: The root holds the `aria-hidden` SVG and a visually hidden text. The text is the `label` prop when given, else `loaderMessages[locale].loading` ("Loading" / "Cargando") from the new `lib/i18n/loader.ts`, read through `useLocale()`. The component is a client component and renders fine inside the server `loading.tsx`, which passes its own label. The root differs by tone:
  - **Page tone**: `<span role="status" aria-live="polite">`. This is the live announcement.
  - **Button tone**: a plain `<span>` with no role. The children of a `<button>` are presentational in ARIA, so a nested `role="status"` is not announced as a live region. The hidden text becomes part of the button's accessible name (a loading Primary button reads as its label plus "Loading") and the button's own `aria-busy` says it is busy. This is what FR-011 and SC-005 mean for a button.
- **Rationale**: FR-011. The drawing is not described. The existing code already uses `role="status"` with text for loading lines, so page-level screen-reader behaviour stays the same. The parity test covers the new text.
- **Alternatives considered**: `aria-label` on a `div`, rejected because a label on an element with no role is not reliably announced. Visible text beside the cauldron, rejected because the spec replaces the text-only lines with the drawing. `role="status"` in every tone, rejected for buttons because it is ignored there and gives a false sense of being announced.
- **Risk and fallback**: A live region that is added to the page together with its text is announced less reliably than one that was already there. Task T035 checks it with VoiceOver on a throttled page. **If the page-level loader is not announced**, the fallback is to mount the `role="status"` root empty and set the hidden text in a `useEffect` right after mount. The picture still shows at once (FR-016 is about the picture), and the region exists before its text does. The cost is that the server-rendered HTML of `loading.tsx` has no text until hydration, so the fallback is applied only if the check fails.

## R10. What gets replaced

- **Decision**: Every row in the call-site table of [contracts/cauldron-loader-ui.md](contracts/cauldron-loader-ui.md). The ten text-only lines (in nine files) count as loading states under FR-015, so they become the loader with their old message as the label. The visible text is dropped. Eight come from a `loading` message. Two more were found by reading every `role="status"` line in `ui/`: "Joining the kitchen…" in `AcceptInvitePanel` while `pending`, and "Checking names…" in `RecipeEditForm`. Status lines that show a **result** (saved, sent, dropped, copied, a toast) are not loading states and stay. Button label swaps such as "Saving…" or "Reading your recipe…" are text on a button and not an animation, so they stay too; a `BaseButton` with `loading` gets the loader.
- **Rationale**: FR-015 says "every existing loading state", not "every animation", and SC-007 checks for animations only. Replacing the text lines too leaves one loading look in the app. Their messages stay as the screen-reader label, so no information is lost for assistive technology.
- **Alternatives considered**: Replace animations only and leave the text lines. It meets SC-007 but breaks the "one shared loader" intent of FR-001 and FR-015. If the owner prefers it, drop those rows; nothing else depends on them.
- **Sweep**: The sweep task greps `ui/` for `animate-spin`, `animate-pulse`, `SpinnerIcon` and `base-button-spin` and expects no match. The grep cannot see text-only waits, so it also lists every `role="status"` line and checks each one by hand against the "wait or result" rule above.
- **Left alone**: The `account.loading` message in `lib/i18n/account.ts` is not used by any screen, so it is not a loading state. It can be removed or kept.

## R11. Deleting the old spinner

- **Decision**: Delete `SpinnerIcon`, its export, its entry in `app/icons/README.md` and the `.spinner` rule and keyframes in `BaseButton.module.scss`.
- **Rationale**: SC-007 and "no other loading animation may remain". `COMPONENT_PATTERNS.md` says each icon has one definition, so a dead icon is removed, not left.
- **Alternatives considered**: Keep the icon unused, rejected because it invites reuse.
