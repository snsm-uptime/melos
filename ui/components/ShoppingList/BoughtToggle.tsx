import type { Locale } from "@/lib/i18n/locale";
import { shoppingListMessages } from "@/lib/i18n/shoppingList";

type BoughtToggleProps = {
  name: string;
  bought: boolean;
  locale: Locale;
  /** Absent on a closed list: the box shows the saved state and cannot change (FR-004). */
  onToggle?: (bought: boolean) => void;
};

/** The bought checkbox of one list item (spec 070 FR-001, FR-018): a real checkbox, so its state is announced. */
export function BoughtToggle({ name, bought, locale, onToggle }: BoughtToggleProps) {
  return (
    <input
      type="checkbox"
      className="size-6 shrink-0 cursor-pointer accent-accent disabled:cursor-default focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent"
      aria-label={shoppingListMessages[locale].markBought(name)}
      checked={bought}
      disabled={!onToggle}
      onChange={(event) => onToggle?.(event.target.checked)}
    />
  );
}

/** Text classes of a bought item: struck through and muted; the checkbox carries the state too (FR-005). */
export function boughtText(bought: boolean | undefined): string {
  return bought ? "text-muted line-through" : "text-foreground";
}
