/**
 * The round action chip that sits on a photo's corner: the side panel's avatar and the recipe
 * photo. A solid surface with a border and shadow, so the icon reads on any photo. Callers add
 * the size and the corner.
 */
export const photoActionClass =
  "absolute inline-flex items-center justify-center rounded-full border border-border bg-surface text-foreground cursor-pointer shadow-sm disabled:opacity-45 disabled:cursor-not-allowed";
