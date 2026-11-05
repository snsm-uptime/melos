# Contract: `DataTable<T>` component

```tsx
<DataTable<T>
  schema={TableSchema<T>}     // columns, search on/off, rowKey (data-model.md)
  rows={T[]}                  // already loaded; never fetched by the table
  locale={Locale}             // collator and labels
  labels={DataTableLabels}    // from lib/i18n/table.ts
  empty={string}              // shown when rows is empty (no search bar acts then)
/>
```

## Behaviour guarantees

1. Sortable heading: a button inside `<th aria-sort>`. Multi-level: a click on an unsorted column adds it as the last level (asc); on a sorted column cycles asc → desc → removed, keeping its level. Sorted headings show the level number and arrow. A "Clear sort" button shows while any level is active. Non-sortable: plain text, no button.
2. Search bar (only when `schema.search`): labelled input above the table; filters as the admin types; clearing restores every row.
3. No matches: the table body is replaced by the `noMatches` text; the input stays focused and editable; a live region announces the count.
4. Sort applies after search (sorts the filtered rows).
5. No network calls, no change to `rows`.

## DataTableLabels (en / es)

| key | en | es |
|---|---|---|
| searchLabel | Search this table | Buscar en esta tabla |
| searchPlaceholder | Search | Buscar |
| noMatches | Nothing matches your search. | Nada coincide con tu búsqueda. |
| matchCount(n) | n rows shown | n filas mostradas |
| sortBy(label) | Sort by {label} | Ordenar por {label} |
| sortLevel(label, level, dir) | {label}, sort level {level}, ascending/descending | {label}, nivel de orden {level}, ascendente/descendente |
| clearSort | Clear sort | Quitar orden |

Spanish wording drafted by the assistant; needs the owner's review.
