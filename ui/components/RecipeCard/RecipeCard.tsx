import Link from "next/link";

import { CartPlusIcon } from "@/app/icons";
import { Chip } from "@/components/Chip";
import { IconButton } from "@/components/IconButton";
import { cartMessages } from "@/lib/i18n/cart";
import type { Locale } from "@/lib/i18n/locale";
import { recipeListMessages } from "@/lib/i18n/recipeLists";
import type { RecipeCard as RecipeCardData } from "@/lib/recipesClient";

type RecipeCardProps = {
  recipe: RecipeCardData;
  locale: Locale;
  /** Shown on kitchen lists, where recipes come from several notebooks (spec 021 FR-004). */
  showNotebook?: boolean;
  /**
   * The list this card is on, with its page and filter. The card links to the recipe detail and
   * Back returns here (spec 027 FR-004). Without it the card is not a link.
   */
  from?: string;
  /**
   * The cart-icon button of kitchen cards (spec 022 FR-017c). Personal notebook lists pass
   * nothing, so their cards have none.
   */
  cart?: CardCart;
};

export type CardCart = {
  inCart: boolean;
  /** Never disabled: a refusal while someone else edits shows a toast (spec 022 FR-017b). */
  onToggle: () => void;
};

/** The default image until a recipe has its own: a cooking pot. */
function PotIcon() {
  return (
    <svg
      viewBox="0 0 24 24"
      width="28"
      height="28"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      data-testid="recipe-pot-icon"
    >
      <path d="M4 10h16v6a4 4 0 0 1-4 4H8a4 4 0 0 1-4-4v-6Z" />
      <path d="M2 10h2M20 10h2" />
      <path d="M9 7c0-1.2 1-1.2 1-2.4M14 7c0-1.2 1-1.2 1-2.4" />
    </svg>
  );
}

/**
 * Recipe card: links to the detail; no categories (spec 021 FR-014, spec 027). Kitchen cards
 * have the cart-icon button (spec 022).
 */
export function RecipeCard({ recipe, locale, showNotebook = false, from, cart }: RecipeCardProps) {
  const t = recipeListMessages[locale];
  const c = cartMessages[locale];
  return (
    <article
      className={`relative flex min-w-0 items-center gap-[var(--space-3)] rounded-[var(--radius-md)] border border-border ${
        cart?.inCart ? "bg-[var(--card-selected)]" : "bg-surface"
      } p-[var(--space-3)]${
        // The title link's overlay makes the whole card the target; show that it is one.
        from ? " cursor-pointer transition-colors hover:border-accent focus-within:border-accent" : ""
      }`}
    >
      <span className="flex flex-shrink-0 items-center justify-center rounded-[var(--radius-md)] bg-background p-[var(--space-4)] text-muted">
        <PotIcon />
      </span>
      <div className="flex min-w-0 flex-1 flex-col gap-[var(--space-1)]">
        <h3
          className="m-0 truncate text-[1rem] font-[550] leading-normal text-foreground"
          title={recipe.title}
        >
          {from ? (
            <Link
              href={`/recipes/${encodeURIComponent(recipe.id)}?from=${encodeURIComponent(from)}`}
              className="text-inherit no-underline after:absolute after:inset-0 after:content-['']"
            >
              {recipe.title}
            </Link>
          ) : (
            recipe.title
          )}
        </h3>
        <div className="flex flex-wrap items-center gap-[var(--space-1)]">
          <Chip tone="accent">{recipe.author_alias ?? t.authorUnknown}</Chip>
          <span className="text-[0.85rem] text-muted">
            {t.ingredients(recipe.ingredient_count)}
          </span>
        </div>
        {showNotebook ? (
          <p className="m-0 truncate text-[0.85rem] text-muted">
            {from && recipe.notebook_id ? (
              // Above the title link's full-card overlay, so it takes its own clicks. Back returns to `from`.
              <Link
                href={`/notebooks/${encodeURIComponent(recipe.notebook_id)}?from=${encodeURIComponent(from)}`}
                className="relative z-10 text-inherit underline underline-offset-2 transition-colors hover:text-accent"
              >
                {recipe.notebook_name}
              </Link>
            ) : (
              recipe.notebook_name
            )}
          </p>
        ) : null}
      </div>
      {cart ? (
        // Above the title link's full-card overlay, so it takes its own clicks.
        <div className="relative z-10 flex-shrink-0">
          <IconButton
            variant="ghost"
            label={cart.inCart ? c.removeFromCart : c.addToCart}
            aria-pressed={cart.inCart}
            tone={cart.inCart ? "danger" : "default"}
            icon={<CartPlusIcon inCart={cart.inCart} className="size-6" />}
            onClick={(event) => {
              event.stopPropagation();
              cart.onToggle();
            }}
          />
        </div>
      ) : null}
    </article>
  );
}
