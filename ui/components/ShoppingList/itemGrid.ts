/**
 * The shopping list's items as columns, so a long list scrolls less. The columns follow the
 * list's own width (the nearest `@container`, the list's section), not the window, so they are
 * set for the Cart page body with the side panel open (16rem panel, page gutters and the
 * section's padding take about 336px off the window):
 *
 * - 1 column below `@2xl` (42rem), phones and tablets: window under about 1008px
 * - 2 columns from `@2xl`, around Tailwind's `lg` (1024px) up to about 1232px
 * - 3 columns from `@4xl` (56rem), around Tailwind's `xl` (1280px)
 * - 4 columns from `@6xl` (72rem), around Tailwind's `2xl` (1536px): window from about 1488px
 */
export const ITEM_GRID =
  "m-0 grid list-none grid-cols-1 gap-2 p-0 @2xl:grid-cols-2 @4xl:grid-cols-3 @6xl:grid-cols-4";
