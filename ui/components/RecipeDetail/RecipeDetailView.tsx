"use client";

import Link from "next/link";
import { useMemo, useState } from "react";

import {
  BackIcon,
  CartPlusIcon,
  DotsIcon,
  LinkIcon,
  PencilIcon,
  ShareIcon,
  TrashIcon,
} from "@/app/icons";
import { useChromeScrolled } from "@/components/ChromeScroll";
import { EditorNotice } from "@/components/Cart/EditorNotice";
import { Chip } from "@/components/Chip";
import { IconButton } from "@/components/IconButton";
import iconButtonStyles from "@/components/IconButton/IconButton.module.scss";
import {
  IconButtonPopup,
  IconButtonPopupItem,
  IconButtonPopupLinkItem,
} from "@/components/IconButtonPopup";
import { ShareRecipeDialog } from "@/components/ShareRecipeDialog";
import { IngredientLineRow } from "@/components/RecipeDraft/IngredientLineRow";
import { StepCard } from "@/components/RecipeDraft/StepCard";
import { Tooltip } from "@/components/Tooltip";
import { cartMessages } from "@/lib/i18n/cart";
import type { Locale } from "@/lib/i18n/locale";
import { messagesFor } from "@/lib/i18n/messages";
import { recipeDetailMessages } from "@/lib/i18n/recipeDetail";
import { recipeShareMessages } from "@/lib/i18n/recipeShare";
import { scaleLine } from "@/lib/recipeScale";
import type { RecipeDetail } from "@/lib/recipesClient";

import { ServingsControl } from "./ServingsControl";

type RecipeDetailViewProps = {
  recipe: RecipeDetail;
  locale: Locale;
  /** The list the member came from (spec 027 FR-004). */
  backHref: string;
  editHref: string;
  onDelete: () => void;
  /** The cart-icon button, for kitchen recipes (spec 022 FR-017c); omit for none. */
  cartAction?: DetailCartAction;
};

export type DetailCartAction = {
  inCart: boolean;
  /** Never disabled: a refusal while someone else edits shows a toast (FR-017b). */
  onToggle: () => void;
};

/**
 * One saved recipe in the layout of the draft review page, display only: the title, the
 * ingredient cards and the step cards are text, with no fields, dropdowns, or move and remove
 * controls. Edit, Share and Delete sit in the chrome's dots menu; Edit and Delete show only to
 * those who can write (spec 027 FR-005). The source page opens from a link icon beside the cart.
 *
 * The servings can be changed to see the amounts for another number (spec 062). The number is
 * state of this component only: it is not stored, not sent, and not passed to Edit, so a reload
 * or a new visit starts again from the saved servings.
 */
export function RecipeDetailView({
  recipe,
  locale,
  backHref,
  editHref,
  onDelete,
  cartAction,
}: RecipeDetailViewProps) {
  const scrolled = useChromeScrolled();
  const t = recipeDetailMessages[locale];
  const shareText = messagesFor(recipeShareMessages, locale);
  const c = cartMessages[locale];
  // Another session edits the recipe: Edit and Delete wait (spec 022 FR-022).
  const lockedBy = recipe.editor && !recipe.editor.is_me ? recipe.editor : null;
  const source = recipe.source?.url ?? null;
  const [servings, setServings] = useState(recipe.base_servings);
  const [sharing, setSharing] = useState(false);
  const scaled = servings !== recipe.base_servings;
  // Always from the saved lines, so going away and back returns to the saved amounts.
  const lines = useMemo(
    () =>
      recipe.ingredient_lines.map((line) =>
        scaleLine(line, servings, recipe.base_servings),
      ),
    [recipe.ingredient_lines, recipe.base_servings, servings],
  );
  return (
    <main className="mx-auto flex w-full flex-col gap-4 md:min-h-0 md:flex-1">
      {sharing ? (
        <ShareRecipeDialog
          recipeId={recipe.id}
          locale={locale}
          open
          onOpenChange={setSharing}
        />
      ) : null}
      <div className="flex flex-col gap-6 pb-8 md:min-h-0 md:flex-1">
        {/* Same insets and Back slot as the draft page and AppShell's chrome header. */}
        <header
        className="frost-bar frost-bar-phone flex items-center gap-2 pt-[max(0.5rem,env(safe-area-inset-top))] max-md:sticky max-md:top-0 max-md:z-10 pr-[max(1rem,env(safe-area-inset-right))] pb-1 pl-[max(0.5rem,env(safe-area-inset-left))]"
        data-frosted={scrolled ? "true" : "false"}
      >
          <div className="flex w-10 shrink-0 items-center justify-start self-center">
            <Link
              href={backHref}
              aria-label={t.back}
              title={t.back}
              className="m-0 inline-flex flex-shrink-0 items-center justify-center rounded-[8px] border-0 bg-transparent p-1 leading-none text-muted transition-all duration-150 hover:text-foreground"
            >
              <BackIcon className="size-6" />
            </Link>
          </div>
          <div className="flex min-w-0 flex-auto flex-col">
            <h1 className="m-0 min-w-0 px-1 py-[0.15rem] text-[1.5rem] font-[550] leading-normal text-foreground">
              {recipe.title}
            </h1>
            <h4 className="m-0 px-1 text-[0.9rem] font-normal text-muted">
              {recipe.notebook.name}
            </h4>
            <div className="flex flex-wrap items-center gap-2 px-1 pt-1 text-[0.85rem] text-muted">
              <span>{t.authorLabel}</span>
              <Chip tone="accent">
                {recipe.author_alias ?? t.authorUnknown}
              </Chip>
            </div>
          </div>
          <div className="flex shrink-0 items-center gap-1 self-start">
            {cartAction ? (
              <IconButton
                variant="ghost"
                label={cartAction.inCart ? c.removeFromCart : c.addToCart}
                aria-pressed={cartAction.inCart}
                tone={cartAction.inCart ? "danger" : "default"}
                icon={
                  <CartPlusIcon inCart={cartAction.inCart} className="size-6" />
                }
                onClick={cartAction.onToggle}
              />
            ) : null}
            {source ? (
              <Tooltip label={t.sourceLink}>
                <a
                  href={source}
                  rel="noopener noreferrer"
                  target="_blank"
                  aria-label={t.sourceLink}
                  className={`m-0 inline-flex flex-shrink-0 items-center justify-center rounded-[8px] border-0 bg-transparent p-1 leading-none text-muted transition-all duration-150 ${iconButtonStyles.button} ${iconButtonStyles.ghost}`}
                >
                  <LinkIcon className="size-6" />
                </a>
              </Tooltip>
            ) : null}
            <IconButtonPopup
              button={
                <IconButton
                  variant="ghost"
                  label={t.options}
                  icon={<DotsIcon className="size-6" />}
                />
              }
            >
              {recipe.can_write ? (
                lockedBy ? (
                  <IconButtonPopupItem disabled icon={<PencilIcon />}>
                    {t.edit}
                  </IconButtonPopupItem>
                ) : (
                  <IconButtonPopupLinkItem href={editHref} icon={<PencilIcon />}>
                    {t.edit}
                  </IconButtonPopupLinkItem>
                )
              ) : null}
              <IconButtonPopupItem
                onClick={() => setSharing(true)}
                icon={<ShareIcon />}
              >
                {shareText.shareButton}
              </IconButtonPopupItem>
              {recipe.can_write ? (
                <IconButtonPopupItem
                  danger
                  disabled={Boolean(lockedBy)}
                  onClick={onDelete}
                  icon={<TrashIcon />}
                >
                  {t.delete}
                </IconButtonPopupItem>
              ) : null}
            </IconButtonPopup>
          </div>
        </header>

        {lockedBy ? (
          <div className="px-4">
            <EditorNotice
              alias={lockedBy.alias}
              kind="recipe"
              locale={locale}
            />
          </div>
        ) : null}

        <div className="flex flex-col gap-6 px-4 md:min-h-0 md:flex-1 md:flex-row">
          {/* The image over the ingredients, one column beside the steps; on mobile the image comes first. */}
          <div className="flex min-w-0 flex-col gap-6 md:min-h-0 md:max-w-[450px] md:flex-1">
            {recipe.preview_image ? (
              // eslint-disable-next-line @next/next/no-img-element -- a stored data URI
              <img
                src={recipe.preview_image}
                alt={recipe.title}
                className="block max-h-72 w-full shrink-0 rounded-[0.75rem] object-cover"
              />
            ) : null}
            <section className="flex min-w-0 flex-col gap-2 md:min-h-0 md:flex-1 md:overflow-hidden">
              <div className="flex shrink-0 items-center justify-between gap-2">
                <h2 className="m-0 text-[1rem] font-[550] text-foreground">
                  {t.ingredientsTitle}
                </h2>
                <ServingsControl
                  value={servings}
                  onChange={setServings}
                  locale={locale}
                />
              </div>
              {scaled || recipe.servings_estimated ? (
                <div className="flex flex-wrap items-center justify-end gap-2 text-[0.85rem] text-muted">
                  {scaled ? <span>{t.makes(recipe.base_servings)}</span> : null}
                  {recipe.servings_estimated ? (
                    <Chip tone="warning">{t.estimated}</Chip>
                  ) : null}
                  {scaled ? (
                    <button
                      type="button"
                      className="text-[0.85rem] text-accent underline underline-offset-2"
                      onClick={() => setServings(recipe.base_servings)}
                    >
                      {t.resetServings}
                    </button>
                  ) : null}
                </div>
              ) : null}
              <div className="flex flex-col gap-2 md:min-h-0 md:flex-1 md:overflow-y-auto">
                <ul className="m-0 flex list-none flex-col gap-2 p-0">
                  {lines.map((line, index) => (
                    <IngredientLineRow
                      key={`${index}-${line.name}`}
                      line={line}
                      readOnly
                      locale={locale}
                    />
                  ))}
                </ul>
              </div>
            </section>
          </div>

          <section className="flex min-w-0 flex-col gap-2 md:min-h-0 md:flex-1 md:overflow-hidden">
            <h2 className="m-0 shrink-0 text-[1rem] font-[550] text-foreground">
              {t.stepsTitle}
            </h2>
            {scaled ? (
              <p className="m-0 text-[0.85rem] text-muted">{t.stepsAsSaved}</p>
            ) : null}
            <div className="flex flex-col gap-2 md:min-h-0 md:flex-1 md:overflow-y-auto">
              <ol className="m-0 flex list-none flex-col p-0">
                {recipe.steps.map((step, index) => (
                  <StepCard
                    key={`${index}-${step.slice(0, 12)}`}
                    index={index}
                    text={step}
                    readOnly
                    locale={locale}
                  />
                ))}
              </ol>
            </div>
          </section>
        </div>

      </div>
    </main>
  );
}
