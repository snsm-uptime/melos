# Contract: feature inventory module

Module: `ui/lib/featureInventory.ts`. Pure data and pure functions; no imports from React, Next.js
or any client. Shapes in [../data-model.md](../data-model.md).

## Exports

```ts
type Localized = { en: string; es: string };
type GroupId = "capture" | "notebooks" | "together" | "shop" | "ingredients" | "home";
type FeatureStatus = "available" | "planned";

type FeatureGroup = { id: GroupId; order: 1 | 2 | 3 | 4 | 5 | 6; title: Localized; lede: Localized };
type Feature = {
  id: string;
  group: GroupId;
  name: Localized;
  summary: Localized;
  stories: readonly string[];
  status: FeatureStatus;
};

export const featureGroups: readonly FeatureGroup[];
export const features: readonly Feature[];
export function groupsInOrder(): readonly FeatureGroup[];
export function availableFeatures(group: GroupId): readonly Feature[];
export function plannedFeatures(): readonly Feature[];
```

## Invariants (checked by `featureInventory.test.ts`)

1. Exactly six groups, ids as above, `order` 1..6 matching capture, notebooks, together, shop,
   ingredients, home.
2. Feature ids are unique.
3. Every `Localized` value has a non-empty, trimmed `en` and `es` (FR-013).
4. Every feature has at least one story matching `/^S-\d{3}$/`.
5. Every group has at least one `available` feature (a section is never empty).
6. A feature appears in exactly one of: its group's available list, the planned list (SC-001).

## Change rule (FR-017)

A story that adds, removes or changes a feature a person can use edits this module in the same
change, and its backlog verification note says so. Moving `planned` to `available` is the only
edit needed when a planned feature ships.
