# Data model: Landing page feature tour

Nothing is stored in the database. The "data" is the feature inventory, a source-code module
(`ui/lib/featureInventory.ts`, research R1). The shapes below are what that module exports; see
[contracts/feature-inventory.md](contracts/feature-inventory.md) for the exact export contract.

## FeatureGroup

| Field | Type | Rules |
|---|---|---|
| `id` | `"capture" \| "notebooks" \| "together" \| "shop" \| "ingredients" \| "home"` | Unique; used as the section anchor (R6). |
| `order` | 1..6 | Unique; capture 1, notebooks 2, together 3, shop 4, ingredients 5, home 6 (spec FR-002, clarification Q3). |
| `title` | `{ en: string; es: string }` | Both non-empty. |
| `lede` | `{ en: string; es: string }` | One or two sentences; both non-empty. |
| `demo` | `DemoId` | One per group; the scene component and its description key. |

## Feature

| Field | Type | Rules |
|---|---|---|
| `id` | kebab-case string | Unique across the inventory. |
| `group` | `FeatureGroup["id"]` | Exactly one group (FR-002). |
| `name` | `{ en: string; es: string }` | Short, both non-empty. |
| `summary` | `{ en: string; es: string }` | One plain sentence, both non-empty. |
| `stories` | `string[]` | At least one backlog id, e.g. `"S-070"`. |
| `status` | `"available" \| "planned"` | See state transitions. |

Order of features inside a group is the array order in the module.

## Demo

| Field | Type | Rules |
|---|---|---|
| `id` | `"overview" \| FeatureGroup["id"]` | Seven demos: the overview in the hero and one per group. |
| `title` | `{ en; es }` (in `landingMessages`) | Labels the demo region. |
| `description` | `{ en; es }` (in `landingMessages`) | Screen-reader text (FR-009). |
| scene | component | Invented data only; final state is its resting style (R2). |

## State transitions

```text
planned ──(story done, feature usable)──▶ available
available ──(feature removed from the app)──▶ entry deleted
```

- `planned`: listed only in the "Coming soon" strip (FR-004).
- `available`: listed only in its group's section.
- The strip is not rendered when no feature is `planned`.

## Derived views (pure functions in the same module)

- `groupsInOrder()`: groups sorted by `order`.
- `availableFeatures(groupId)`: features of a group with status `available`, in array order.
- `plannedFeatures()`: all `planned` features, in array order.
