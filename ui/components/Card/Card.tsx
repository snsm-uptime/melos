import type { ReactNode } from "react";

type CardElement = "article" | "section" | "div" | "li";

export type CardProps = {
  children: ReactNode;
  /** The element to render, so a card can be a list item without an extra wrapper. */
  as?: CardElement;
  className?: string;
};

type CardPartProps = {
  children: ReactNode;
  className?: string;
};

/** Surface fill, hairline border and the resting 2dp shadow. */
export const cardClassName =
  "flex min-w-0 flex-col overflow-hidden rounded-[var(--radius-lg)] border border-border bg-surface shadow-2dp";

/** A raised surface. Compose with `CardHeader` and `CardBody`, or put content in it directly. */
export function Card({ children, as: Element = "div", className }: CardProps) {
  return <Element className={`${cardClassName} ${className ?? ""}`}>{children}</Element>;
}

/** The card's top band, set apart from the body by a divider; no divider when nothing follows it. */
export function CardHeader({ children, className }: CardPartProps) {
  return (
    <div
      className={`border-b border-border last:border-b-0 px-[var(--space-4)] py-[var(--space-3)] ${className ?? ""}`}
    >
      {children}
    </div>
  );
}

export function CardBody({ children, className }: CardPartProps) {
  return (
    <div
      className={`flex flex-col gap-[var(--space-2)] px-[var(--space-4)] py-[var(--space-3)] ${className ?? ""}`}
    >
      {children}
    </div>
  );
}
