"use client";

import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";

import { CartIcon, ShareIcon } from "@/app/icons";
import { ActionDialog } from "@/components/ActionDialog";
import { Avatar } from "@/components/Avatar";
import { useChromeHeader } from "@/components/ChromeBack";
import { Badge } from "@/components/Badge";
import { IconButton } from "@/components/IconButton";
import type { Locale } from "@/lib/i18n/locale";
import { shoppingListMessages } from "@/lib/i18n/shoppingList";
import { SectionLabel } from "@/components/soft-ledger/SectionLabel";
import { useKitchenCartCount } from "./cartCount";
import { InviteForm, type InviteFormMessages } from "./InviteForm";
import { memberLabel, type KitchenMember } from "./kitchensClient";

export type KitchenShare = {
  kitchenId: string;
  ownerId: string | undefined;
  members: KitchenMember[];
  membersLoadError: boolean;
  inviteMessages: InviteFormMessages;
  labels: {
    /** The share button's accessible name. */
    open: string;
    close: string;
    membersTitle: string;
    ownerBadge: string;
    loadError: string;
  };
};

type Props = {
  title: string;
  /** Owner only: adds the share button at the end of the chrome and its dialog. */
  share?: KitchenShare;
  /**
   * Every member: a cart button before the share button that opens the kitchen's cart. A circular
   * badge on its bottom right corner shows how many recipes are in the cart, in the given language.
   */
  cart?: { href: string; label: string; locale: Locale };
};

/** Opts kitchen detail into AppShell Back + title, the cart button and the owner's share button. */
export function KitchenDetailChrome({ title, share, cart }: Props) {
  const { push } = useRouter();
  const [open, setOpen] = useState(false);
  const openLabel = share?.labels.open;
  const cartHref = cart?.href;
  const cartLabel = cart?.label;
  const cartLocale = cart?.locale;
  const cartCount = useKitchenCartCount();

  const trailing = useMemo(
    () =>
      openLabel || cartHref ? (
        <>
          {cartHref && cartLabel && cartLocale ? (
            <IconButton
              type="button"
              variant="ghost"
              label={
                cartCount
                  ? `${cartLabel}, ${shoppingListMessages[cartLocale].recipeCount(cartCount)}`
                  : cartLabel
              }
              onClick={() => push(cartHref)}
              icon={
                <span className="relative inline-flex">
                  <CartIcon className="size-6" />
                  {cartCount ? (
                    <Badge
                      size="sm"
                      count={cartCount}
                      label={shoppingListMessages[cartLocale].recipeCount(cartCount)}
                      className="absolute -bottom-1 -right-1.5 ring-2 ring-background"
                    />
                  ) : null}
                </span>
              }
            />
          ) : null}
          {openLabel ? (
            <IconButton
              type="button"
              variant="ghost"
              label={openLabel}
              aria-haspopup="dialog"
              onClick={() => setOpen(true)}
              icon={<ShareIcon className="size-6" />}
            />
          ) : null}
        </>
      ) : undefined,
    [openLabel, cartHref, cartLabel, cartLocale, cartCount, push],
  );

  useChromeHeader({
    backHref: "/home",
    title,
    trailing,
  });

  if (!share) return null;

  return (
    <ActionDialog
      open={open}
      title={share.inviteMessages.inviteTitle}
      cancelLabel={share.labels.close}
      onOpenChange={setOpen}
    >
      <div className="flex flex-col gap-[var(--space-4)]">
        <InviteForm
          kitchenId={share.kitchenId}
          messages={share.inviteMessages}
          reserveErrorHeight
          hideBorder
        />
        <section className="flex flex-col gap-[var(--space-2)]">
          <SectionLabel>{share.labels.membersTitle}</SectionLabel>
          {share.membersLoadError ? (
            <p className="m-0 text-muted" role="alert">
              {share.labels.loadError}
            </p>
          ) : (
            <ul className="m-0 flex max-h-[40vh] list-none flex-col gap-[var(--space-2)] overflow-y-auto p-0">
              {share.members.map((member) => (
                <li key={member.user_id} className="flex items-center gap-[var(--space-2)]">
                  <Avatar
                    alias={member.alias}
                    seed={member.user_id}
                    photoBase64={member.photo_base64 ?? null}
                  />
                  <span>{memberLabel(member)}</span>
                  {member.user_id === share.ownerId ? (
                    <span className="text-[0.85rem] text-muted">{share.labels.ownerBadge}</span>
                  ) : null}
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>
    </ActionDialog>
  );
}
