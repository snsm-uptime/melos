import { PlusIcon } from "@/app/icons";

export type AddItemCardProps = {
  /** The accessible name; kept as screen-reader text too, since the card only shows a plus. */
  label: string;
  onClick: () => void;
  disabled?: boolean;
  className?: string;
};

/**
 * The shared "add an item" call to action: a dashed card with a plus icon, used wherever a list
 * grows by one (a recipe in a notebook grid, a step in a recipe form). Same radius and fill as
 * `Card`; on hover it lifts and takes the accent colour.
 */
export function AddItemCard({ label, onClick, disabled, className }: AddItemCardProps) {
  return (
    <button
      type="button"
      aria-label={label}
      onClick={onClick}
      disabled={disabled}
      className={`flex w-full cursor-pointer items-center justify-center rounded-[var(--radius-md)] border border-dashed border-border bg-surface text-muted transition-[color,border-color,box-shadow,transform] duration-150 enabled:hover:-translate-y-0.5 enabled:hover:border-accent enabled:hover:text-accent enabled:hover:shadow-elevation-1 focus-visible:border-accent focus-visible:text-accent disabled:cursor-not-allowed disabled:opacity-65 motion-reduce:transition-none motion-reduce:hover:translate-y-0 ${className ?? ""}`}
    >
      <PlusIcon />
      <span className="sr-only">{label}</span>
    </button>
  );
}
