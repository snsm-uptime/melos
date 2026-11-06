import Link from "next/link";

import { Chip, chipClassName } from "./Chip";

/** A chip's text, or a chip that opens a page. */
export type CountChipItem = string | null | { label: string; href: string };

/** A count, then one chip per item in a row that scrolls sideways (table cells, spec 066). */
export function CountChips({
  count,
  names,
  fallback,
}: {
  count: number;
  /** A null item shows `fallback` (an account with no alias). */
  names: ReadonlyArray<CountChipItem> | undefined;
  fallback?: string;
}) {
  const list = Array.isArray(names) ? names : [];
  return (
    <div className="flex min-w-0 items-center gap-3">
      <span className="shrink-0 font-semibold">{String(count)}</span>
      {/* The row fills the cell; `w-0 min-w-full` keeps the chips from widening the table, so it
          scrolls only when the space the table gives the column is too small for them. */}
      <div className="min-w-[12rem] flex-1">
        <div className="flex w-0 min-w-full gap-1 overflow-x-auto pb-1">
          {list.map((item, index) =>
            item !== null && typeof item === "object" ? (
              <Link
                key={index}
                href={item.href}
                className={`${chipClassName.muted} no-underline hover:border-accent hover:text-accent focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent`}
              >
                {item.label}
              </Link>
            ) : (
              <Chip key={index}>
                {typeof item === "string" ? item : (fallback ?? "")}
              </Chip>
            ),
          )}
        </div>
      </div>
    </div>
  );
}
