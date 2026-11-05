import Link from "next/link";

import { CartPlusIcon, PotIcon } from "@/app/icons";
import { linkCardClassName } from "@/components/Card";
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
  /**
   * Stand upright even without an image, the pot icon in the photo's place, so the card matches
   * image cards on the same list.
   */
  upright?: boolean;
};

export type CardCart = {
  inCart: boolean;
  /** Never disabled: a refusal while someone else edits shows a toast (spec 022 FR-017b). */
  onToggle: () => void;
};

/**
 * Recipe card: links to the detail; no categories (spec 021 FR-014, spec 027). Kitchen cards
 * have the cart-icon button (spec 022).
 */
export function RecipeCard({
  recipe,
  locale,
  showNotebook = false,
  from,
  cart,
  upright = false,
}: RecipeCardProps) {
  const t = recipeListMessages[locale];
  const c = cartMessages[locale];
  // With an image the card stands upright: the photo on top, the text under it.
  const image = recipe.preview_image ?? null;
  const tall = image !== null || upright;
  const details = (
    <>
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
    </>
  );
  return (
    // `isolate` keeps the z-10 of the link and cart control inside the card; they only need to
    // clear the title link's overlay, and must not paint over the app's open menus.
    <article
      className={`relative isolate flex min-w-0 rounded-[var(--radius-md)] border border-border ${
        tall
          ? // Two parts: the photo on top, the metadata under it; as wide as the photo at most.
            "h-full w-full max-w-[200px] flex-col overflow-hidden"
          : "items-center gap-[var(--space-3)] p-[var(--space-3)]"
      } ${cart?.inCart ? "bg-[var(--card-selected)]" : "bg-surface"}${
        // The title link's overlay makes the whole card the target; show that it is one.
        from ? ` ${linkCardClassName}` : ""
      }`}
    >
      {image ? (
        // Fills the card's width; the ratio keeps the photo in proportion. The card clips its corners.
        // eslint-disable-next-line @next/next/no-img-element -- a data URI, not a site address
        <img
          src={image}
          alt=""
          loading="lazy"
          data-testid="recipe-card-image"
          className="block aspect-[4/3] w-full flex-shrink-0 bg-background object-cover"
        />
      ) : tall ? (
        // The photo's place, same ratio, so this card has the image cards' shape.
        <span
          data-testid="recipe-card-placeholder"
          className="flex aspect-[4/3] w-full flex-shrink-0 items-center justify-center bg-background text-muted"
        >
          <PotIcon />
        </span>
      ) : (
        <span className="flex flex-shrink-0 items-center justify-center rounded-[var(--radius-md)] bg-background p-[var(--space-4)] text-muted">
          <PotIcon />
        </span>
      )}
      {tall ? (
        <div className="flex min-w-0 items-start gap-[var(--space-2)] p-[var(--space-3)]">
          {details}
        </div>
      ) : (
        details
      )}
    </article>
  );
}
