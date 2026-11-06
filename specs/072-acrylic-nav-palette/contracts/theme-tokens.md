# Contract: Theme tokens

The palette is a contract between `ui/app/globals.css` and every component: components use only
these roles (through Tailwind `--color-*` utilities or `var(--role)`), never raw colours.
`ui/app/palette.test.ts` reads `globals.css` and checks every pair below.

## Values

| Property | Light (`:root`) | Dark (`html.dark` and `prefers-color-scheme: dark`) |
|----------|-----------------|------------------------------------------------------|
| `--background` | `#f7f5fa` | `#141218` |
| `--surface` | `#ffffff` | `#201d27` |
| `--foreground` | `#1d1a24` | `#e5e7eb` |
| `--muted` | `#5f596b` | `#a5adba` |
| `--border` | `#e4e0ea` | `#36313f` |
| `--field-border` | `#8b8497` | `#756e82` |
| `--accent` | `#ab5a00` | `#fd9c21` |
| `--accent-fill` | `#fd9c21` | `#fd9c21` |
| `--on-accent` | `#141218` | `#141218` |
| `--primary` | `#9035d6` | `#6d1aad` |
| `--on-primary` | `#ffffff` | `#ffffff` |
| `--secondary` | `#d82591` | `#d82591` |
| `--on-secondary` | `#ffffff` | `#ffffff` |
| `--error` | `#c42727` | `#f87171` |
| `--danger` | `#b91c1c` | `#f26363` |
| `--danger-strong` | `#d32f2f` | `#d32f2f` |
| `--warn` | `#8a6a00` | `#facc15` |
| `--owed` | `#15803d` | `#4ade80` |
| `--cauldron-body` | `#ac79c4` | `#806595` |
| `color-scheme` | `light` | `dark` |

Derived (same formula in both themes):

```css
--menu-item-hover:    color-mix(in srgb, var(--accent-fill) 10%, var(--surface));
--menu-item-selected: color-mix(in srgb, var(--accent-fill) 22%, var(--surface));
--card-selected:      color-mix(in srgb, var(--accent-fill) 12%, var(--surface));
```

Tailwind exposure added to `@theme`: `--color-primary`, `--color-on-primary`,
`--color-accent-fill`, `--color-field-border`.

## Usage rules

- Filled actions (`PrimaryButton`, Save/Confirm/Add, the capture sheets' submit, shopping "Done"):
  `bg-primary text-on-primary`.
- Orange areas that carry text (badges, selected pills, selected day): `bg-accent-fill text-on-accent`.
- Orange text, icons, selected outlines, focus rings, radio and checkbox marks: `--accent`.
- Inputs, selects, textareas, checkboxes: `border-field-border`; focus switches to `--accent`.
- Warnings always carry an icon or wording, never colour alone (FR-012).

## Contrast check (SC-003)

Frosted rows assume the worst content beneath: pure black or pure white, with the frost at
`--frost-alpha` (86%). All 70 pairs pass (the two "Text on danger fill" rows were added after the plan: `kitchens.module.scss` `.primaryDanger` puts white text on `--danger-strong`, which rules out `#ef4444` in dark at 3.76:1).

### dark

| Pair | Ink | Ground | Values | Ratio | Min | |
|---|---|---|---|---|---|---|
| Text on page | `--foreground` | `--background` | `#e5e7eb` on `#141218` | 15.02 | 4.5 | pass |
| Text on surface | `--foreground` | `--surface` | `#e5e7eb` on `#201d27` | 13.39 | 4.5 | pass |
| Quiet text on page | `--muted` | `--background` | `#a5adba` on `#141218` | 8.22 | 4.5 | pass |
| Quiet text on surface | `--muted` | `--surface` | `#a5adba` on `#201d27` | 7.33 | 4.5 | pass |
| Main colour text/icon on page | `--accent` | `--background` | `#fd9c21` on `#141218` | 8.81 | 4.5 | pass |
| Main colour text/icon on surface | `--accent` | `--surface` | `#fd9c21` on `#201d27` | 7.86 | 4.5 | pass |
| Text on orange fill | `--on-accent` | `--accent-fill` | `#141218` on `#fd9c21` | 8.81 | 4.5 | pass |
| Text on violet fill | `--on-primary` | `--primary` | `#ffffff` on `#6d1aad` | 8.74 | 4.5 | pass |
| Text on magenta fill | `--on-secondary` | `--secondary` | `#ffffff` on `#d82591` | 4.57 | 4.5 | pass |
| Text on danger fill | `#ffffff` | `--danger-strong` | `#ffffff` on `#d32f2f` | 4.98 | 4.5 | pass |
| Error text on page | `--error` | `--background` | `#f87171` on `#141218` | 6.72 | 4.5 | pass |
| Error text on surface | `--error` | `--surface` | `#f87171` on `#201d27` | 5.99 | 4.5 | pass |
| Danger text on surface | `--danger` | `--surface` | `#f26363` on `#201d27` | 5.32 | 4.5 | pass |
| Warning text on page | `--warn` | `--background` | `#facc15` on `#141218` | 12.14 | 4.5 | pass |
| Warning text on surface | `--warn` | `--surface` | `#facc15` on `#201d27` | 10.83 | 4.5 | pass |
| Success text on page | `--owed` | `--background` | `#4ade80` on `#141218` | 10.67 | 4.5 | pass |
| Success text on surface | `--owed` | `--surface` | `#4ade80` on `#201d27` | 9.52 | 4.5 | pass |
| Input border on surface | `--field-border` | `--surface` | `#756e82` on `#201d27` | 3.40 | 3 | pass |
| Input border on page | `--field-border` | `--background` | `#756e82` on `#141218` | 3.82 | 3 | pass |
| Focus ring on page | `--accent` | `--background` | `#fd9c21` on `#141218` | 8.81 | 3 | pass |
| Focus ring on surface | `--accent` | `--surface` | `#fd9c21` on `#201d27` | 7.86 | 3 | pass |
| Text on hovered menu row | `--foreground` | `--menu-item-hover` | `#e5e7eb` on `#362a26` | 11.19 | 4.5 | pass |
| Text on selected menu row | `--foreground` | `--menu-item-selected` | `#e5e7eb` on `#513926` | 8.64 | 4.5 | pass |
| Text on selected card | `--foreground` | `--card-selected` | `#e5e7eb` on `#3b2c26` | 10.77 | 4.5 | pass |
| Quiet text on selected card | `--muted` | `--card-selected` | `#a5adba` on `#3b2c26` | 5.90 | 4.5 | pass |
| Text on frosted bar over black | `--foreground` | `bar/black` | `#e5e7eb` on `#121015` | 15.27 | 4.5 | pass |
| Text on frosted bar over white | `--foreground` | `bar/white` | `#e5e7eb` on `#302e34` | 10.83 | 4.5 | pass |
| Quiet text on frosted bar over black | `--muted` | `bar/black` | `#a5adba` on `#110f15` | 8.40 | 4.5 | pass |
| Quiet text on frosted bar over white | `--muted` | `bar/white` | `#a5adba` on `#353338` | 5.51 | 4.5 | pass |
| Icon (main colour) on frosted bar over black | `--accent` | `bar/black` | `#fd9c21` on `#121015` | 8.96 | 3 | pass |
| Icon (main colour) on frosted bar over white | `--accent` | `bar/white` | `#fd9c21` on `#302e34` | 6.36 | 3 | pass |
| Text on frosted menu over black | `--foreground` | `menu/black` | `#e5e7eb` on `#1c1a22` | 13.90 | 4.5 | pass |
| Text on frosted menu over white | `--foreground` | `menu/white` | `#e5e7eb` on `#3b3841` | 9.28 | 4.5 | pass |
| Quiet text on frosted menu over black | `--muted` | `menu/black` | `#a5adba` on `#1c1922` | 7.68 | 4.5 | pass |
| Quiet text on frosted menu over white | `--muted` | `menu/white` | `#a5adba` on `#3f3d45` | 4.74 | 4.5 | pass |

### light

| Pair | Ink | Ground | Values | Ratio | Min | |
|---|---|---|---|---|---|---|
| Text on page | `--foreground` | `--background` | `#1d1a24` on `#f7f5fa` | 15.83 | 4.5 | pass |
| Text on surface | `--foreground` | `--surface` | `#1d1a24` on `#ffffff` | 17.14 | 4.5 | pass |
| Quiet text on page | `--muted` | `--background` | `#5f596b` on `#f7f5fa` | 6.20 | 4.5 | pass |
| Quiet text on surface | `--muted` | `--surface` | `#5f596b` on `#ffffff` | 6.71 | 4.5 | pass |
| Main colour text/icon on page | `--accent` | `--background` | `#ab5a00` on `#f7f5fa` | 4.62 | 4.5 | pass |
| Main colour text/icon on surface | `--accent` | `--surface` | `#ab5a00` on `#ffffff` | 5.01 | 4.5 | pass |
| Text on orange fill | `--on-accent` | `--accent-fill` | `#141218` on `#fd9c21` | 8.81 | 4.5 | pass |
| Text on violet fill | `--on-primary` | `--primary` | `#ffffff` on `#9035d6` | 5.73 | 4.5 | pass |
| Text on magenta fill | `--on-secondary` | `--secondary` | `#ffffff` on `#d82591` | 4.57 | 4.5 | pass |
| Text on danger fill | `#ffffff` | `--danger-strong` | `#ffffff` on `#d32f2f` | 4.98 | 4.5 | pass |
| Error text on page | `--error` | `--background` | `#c42727` on `#f7f5fa` | 5.29 | 4.5 | pass |
| Error text on surface | `--error` | `--surface` | `#c42727` on `#ffffff` | 5.73 | 4.5 | pass |
| Danger text on surface | `--danger` | `--surface` | `#b91c1c` on `#ffffff` | 6.47 | 4.5 | pass |
| Warning text on page | `--warn` | `--background` | `#8a6a00` on `#f7f5fa` | 4.68 | 4.5 | pass |
| Warning text on surface | `--warn` | `--surface` | `#8a6a00` on `#ffffff` | 5.07 | 4.5 | pass |
| Success text on page | `--owed` | `--background` | `#15803d` on `#f7f5fa` | 4.63 | 4.5 | pass |
| Success text on surface | `--owed` | `--surface` | `#15803d` on `#ffffff` | 5.02 | 4.5 | pass |
| Input border on surface | `--field-border` | `--surface` | `#8b8497` on `#ffffff` | 3.59 | 3 | pass |
| Input border on page | `--field-border` | `--background` | `#8b8497` on `#f7f5fa` | 3.32 | 3 | pass |
| Focus ring on page | `--accent` | `--background` | `#ab5a00` on `#f7f5fa` | 4.62 | 3 | pass |
| Focus ring on surface | `--accent` | `--surface` | `#ab5a00` on `#ffffff` | 5.01 | 3 | pass |
| Text on hovered menu row | `--foreground` | `--menu-item-hover` | `#1d1a24` on `#fff5e9` | 15.90 | 4.5 | pass |
| Text on selected menu row | `--foreground` | `--menu-item-selected` | `#1d1a24` on `#ffe9ce` | 14.52 | 4.5 | pass |
| Text on selected card | `--foreground` | `--card-selected` | `#1d1a24` on `#fff3e4` | 15.66 | 4.5 | pass |
| Quiet text on selected card | `--muted` | `--card-selected` | `#5f596b` on `#fff3e4` | 6.14 | 4.5 | pass |
| Text on frosted bar over black | `--foreground` | `bar/black` | `#1d1a24` on `#d9d8dc` | 12.08 | 4.5 | pass |
| Text on frosted bar over white | `--foreground` | `bar/white` | `#1d1a24` on `#f8f6fb` | 15.97 | 4.5 | pass |
| Quiet text on frosted bar over black | `--muted` | `bar/black` | `#5f596b` on `#d9d8dc` | 4.73 | 4.5 | pass |
| Quiet text on frosted bar over white | `--muted` | `bar/white` | `#5f596b` on `#f8f6fb` | 6.26 | 4.5 | pass |
| Icon (main colour) on frosted bar over black | `--accent` | `bar/black` | `#ab5a00` on `#d9d8dc` | 3.52 | 3 | pass |
| Icon (main colour) on frosted bar over white | `--accent` | `bar/white` | `#ab5a00` on `#f8f6fb` | 4.67 | 3 | pass |
| Text on frosted menu over black | `--foreground` | `menu/black` | `#1d1a24` on `#e0e0e0` | 12.98 | 4.5 | pass |
| Text on frosted menu over white | `--foreground` | `menu/white` | `#1d1a24` on `#ffffff` | 17.14 | 4.5 | pass |
| Quiet text on frosted menu over black | `--muted` | `menu/black` | `#5f596b` on `#e0e0e0` | 5.09 | 4.5 | pass |
| Quiet text on frosted menu over white | `--muted` | `menu/white` | `#5f596b` on `#ffffff` | 6.71 | 4.5 | pass |
