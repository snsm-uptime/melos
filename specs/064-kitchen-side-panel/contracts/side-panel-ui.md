# Contract: Side panel UI

## Regions, top to bottom

1. Fixed: open or close control, avatar (link to `/account`, `aria-current` there), alias and "N recipes" (open only).
2. Scrolls: Home; "Kitchens" row with "+" and the archive toggle (row text and toggle open only, "+" in both states); other kitchens A to Z; Notebooks.
3. Fixed: divider, log out.

With the archive toggle on, the kitchen entries are archived kitchens. Home and Notebooks do not change. With no other kitchens, the group has no entries.

## States

| | `md` and up | Below `md` |
|---|---|---|
| Closed | Icons only, tooltip and accessible name on each | Not shown |
| Open | Icons and labels, pushes the content | Drawer over the content with a backdrop |
| Persisted | Yes | No; closes on choosing an entry |

## Current entry

`panelEntryFromPath(pathname, defaultKitchenId)`:

| Path | Entry |
|---|---|
| `/kitchens/{default}` and below | Home |
| `/kitchens/{other}` and below | That kitchen |
| `/notebooks...`, `/recipes/...` | Notebooks |
| `/account...` | Avatar |

## Kitchen header row

| Action | Who | When |
|---|---|---|
| Cart | Member | Always, as today |
| Set as default | Member | Active and not the default |
| Invite, rename, delete | Owner | Limits as today |
| Archive or restore | Owner | Follows the kitchen's state |

Below `md`, set default, rename, archive or restore and delete are in the dots menu. After archive or delete, the person goes to `/home`. Delete keeps its confirmation.

## Choosing a kitchen

Calls `setLastOpenedKitchen`, then navigates. Home does the same with the default.

## Amendment (2026-10-30)

Replaces the Home entry and the account page wherever the text above mentions them:

- There is no Home entry. The default kitchen is first in the kitchen list with a filled star; the others follow A to Z with an outline star at the end of the row, which makes that kitchen the default. Archived kitchens have no star. `/home` remains only as the landing redirect and the no-kitchens prompt.
- `/account` is gone. Photo edits sit on the panel avatar. A Settings entry above Log out opens theme, language and password reset; opening it from the closed panel widens the panel.
