# Component Patterns

This document establishes patterns and standards for building reusable components in the Warm Balance UI. Follow these guidelines when creating new components to maintain consistency, discoverability, and ease of maintenance.

## Icon Management

### Overview
All custom SVG icons are centralized in `/app/icons/` to improve maintainability, reduce duplication, and make it easier to track icon usage across the application.

**Single source of truth:** Every icon has one definition, and all icon documentation lives in [`app/icons/README.md`](./app/icons/README.md): the catalog, usage, design standards, and how to add an icon. Do not duplicate icon docs elsewhere.

### Icon Usage Rules

✅ **Do:**
- Use centralized icons from `/app/icons`
- Reuse existing icons before creating new ones
- Apply styling via CSS modules or inline styles on parent containers
- Pair icon-only buttons with `aria-label` for accessibility
- Use SVG props for semantic attributes (`aria-label`, `title`, etc.)

❌ **Don't:**
- Define inline SVG icons in components
- Create duplicate icon definitions
- Hardcode viewBox dimensions in component markup
- Use icons without proper accessibility labels on icon-only controls

## Future Component Patterns

As you build more shared components, add sections here for:
- Button variants and states
- Form input patterns
- Modal/dialog structure
- Card and list item patterns
- Loading states and skeletons
- Error states and validation
- etc.

Document the pattern, show examples, and link to implementations.

## Component File Organization

### Naming Conventions
- **Components:** PascalCase (e.g., `SaveIcon.tsx`, `UserCard.tsx`)
- **CSS Modules:** camelCase with component name (e.g., `UserCard.module.css`)
- **Exported functions:** PascalCase matching file name

### Import Order
1. React and Next.js imports
2. Centralized shared imports (`@/app/icons`, etc.)
3. Local imports (relative paths)
4. Styles

```tsx
import { useState } from "react";
import Link from "next/link";

import { SaveIcon } from "@/app/icons";
import { UserCard } from "./UserCard";
import styles from "./MyComponent.module.css";
```

### Prop Typing
- Use explicit types over `any`
- Extract complex prop objects into `type` declarations
- For flexible components, use React's `SVGProps<SVGSVGElement>` or similar type spreads

```tsx
import type { SVGProps } from "react";

export function MyIcon({ className, ...props }: SVGProps<SVGSVGElement>) {
  return <svg className={className} {...props} />;
}
```

## CSS and Styling

See `/ui/README.md` Styling section for the canonical approach:
- **Default:** Tailwind CSS utilities co-located in components
- **Custom only:** `*.module.scss` for complex selectors, animations, or custom styles
- **Tokens:** Use CSS variables from `globals.css` (Warm Balance light/dark + Soft-Ledger spacing/shape)

When styling components with icons:
- Style the container button/div; let icons inherit `currentColor`
- Use CSS variables for color themes (`--accent`, `--muted`, `--foreground`, etc.)
- Avoid hardcoding colors in icon components

## Testing Components

- Include unit tests for stateful components
- Test keyboard navigation and focus management for interactive components
- Verify accessibility: ARIA labels, semantic HTML, keyboard support
- Test dark mode by inspecting CSS variable inheritance

## Documentation

Every reusable component should have:
1. **JSDoc comment** describing purpose and props
2. **Usage example** in the component file or nearby README
3. **Reference in COMPONENT_PATTERNS.md** if it's a commonly reused pattern

Example:
```tsx
/**
 * Icon-only submit button. Enabled when form is dirty; muted disabled look when nothing changed.
 * @param variant - 'save' for persist actions, 'send' for invitations
 * @param label - Accessible name (also used as tooltip via title)
 */
export function FormIconSubmit({ variant = "save", label, ...rest }: FormIconSubmitProps) {
  // ...
}
```

## Related References

- **Icon reference:** `app/icons/README.md`
- **Styling guide:** `README.md` Styling section
- **Project architecture:** See `/architecture/ARCHITECTURE-SPINE.md` in planning artifacts
- **Tailwind config:** `tailwind.config.ts`
- **CSS variables:** `globals.css`
