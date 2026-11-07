export type BadgeProps = (
  | {
      /** The number shown. Above 99 it reads "99+" so the circle keeps its shape. */
      count: number;
      /** The accessible name, for example "3 recipes"; the bare number alone says nothing to a screen reader. */
      label: string;
    }
  /** No count: an empty circle, decorative, for a marker its parent already names. */
  | { count?: undefined; label?: undefined }
) & {
  /** "sm" is for pinning on an icon; "md" stands alone. */
  size?: "sm" | "md";
  className?: string;
};

const sizeClassName = {
  sm: "h-4 min-w-4 px-1 text-[0.625rem]",
  md: "h-6 min-w-6 px-1.5 text-[0.75rem]",
} as const;

/** A small filled circle, holding a count or empty. Display only, not interactive. */
export function Badge({ count, label, size = "md", className }: BadgeProps) {
  const classes = `inline-flex flex-shrink-0 items-center justify-center rounded-full bg-accent-fill font-[600] leading-none tabular-nums text-on-accent ${sizeClassName[size]}${className ? ` ${className}` : ""}`;
  if (count === undefined) return <span aria-hidden="true" className={classes} />;
  return (
    <span role="img" aria-label={label} className={classes}>
      <span aria-hidden="true">{count > 99 ? "99+" : count}</span>
    </span>
  );
}
