export type BadgeProps = {
  /** The number shown. Above 99 it reads "99+" so the circle keeps its shape. */
  count: number;
  /** The accessible name, for example "3 recipes"; the bare number alone says nothing to a screen reader. */
  label: string;
  /** "sm" is for pinning on an icon; "md" stands alone. */
  size?: "sm" | "md";
  className?: string;
};

const sizeClassName = {
  sm: "h-4 min-w-4 px-1 text-[0.625rem]",
  md: "h-6 min-w-6 px-1.5 text-[0.75rem]",
} as const;

/** A small filled circle holding a count. Display only, not interactive. */
export function Badge({ count, label, size = "md", className }: BadgeProps) {
  return (
    <span
      role="img"
      aria-label={label}
      className={`inline-flex flex-shrink-0 items-center justify-center rounded-full bg-accent font-[600] leading-none tabular-nums text-on-accent ${sizeClassName[size]}${className ? ` ${className}` : ""}`}
    >
      <span aria-hidden="true">{count > 99 ? "99+" : count}</span>
    </span>
  );
}
