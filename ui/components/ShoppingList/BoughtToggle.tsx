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
export function BoughtToggle({
  name,
  bought,
  locale,
  onToggle,
}: BoughtToggleProps) {
  return (
    <span className="relative inline-grid size-6 shrink-0 place-items-center">
      <input
        type="checkbox"
        className="peer m-0 size-6 cursor-pointer appearance-none rounded-[var(--radius-md)] border border-border bg-background checked:border-accent checked:bg-accent disabled:cursor-default focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
        aria-label={shoppingListMessages[locale].markBought(name)}
        checked={bought}
        disabled={!onToggle}
        onChange={(event) => onToggle?.(event.target.checked)}
      />
      <svg
        aria-hidden="true"
        viewBox="0 0 16 16"
        className="pointer-events-none absolute hidden size-4 text-on-accent peer-checked:block"
      >
        <path
          d="M3.5 8.5l3 3 6-7"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
    </span>
  );
}

/** Text classes of a bought item: struck through and muted; the checkbox carries the state too (FR-005). */
export function boughtText(bought: boolean | undefined): string {
  return bought ? "text-muted line-through" : "text-foreground";
}
