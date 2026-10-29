import type { Locale } from "@/lib/i18n/locale";
import { cartMessages } from "@/lib/i18n/cart";

type EditorNoticeProps = {
  /** The editor's alias; null reads "unknown". */
  alias: string | null;
  kind: "cart" | "recipe";
  locale: Locale;
};

/** "{alias} is editing the cart / this recipe": shown while someone else holds the lock. */
export function EditorNotice({ alias, kind, locale }: EditorNoticeProps) {
  const t = cartMessages[locale];
  const name = alias ?? t.unknown;
  return (
    <p
      role="status"
      className="m-0 rounded-[var(--radius-md)] border border-border bg-surface px-3 py-2 text-[0.9rem] text-muted"
    >
      {kind === "cart" ? t.editingCart(name) : t.editingRecipe(name)}
    </p>
  );
}
