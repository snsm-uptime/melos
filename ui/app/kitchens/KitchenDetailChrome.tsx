"use client";

import { useRouter } from "next/navigation";
import { useMemo, useState, type ReactNode } from "react";

import {
  ArchiveToggleIcon,
  CartIcon,
  DotsIcon,
  StarIcon,
  PencilIcon,
  ShareIcon,
  TrashIcon,
} from "@/app/icons";
import { ActionDialog } from "@/components/ActionDialog";
import { Avatar } from "@/components/Avatar";
import { useChromeHeader } from "@/components/ChromeBack";
import { Badge } from "@/components/Badge";
import { IconButton } from "@/components/IconButton";
import { IconButtonPopup, IconButtonPopupItem } from "@/components/IconButtonPopup";
import { useToast } from "@/components/Toast";
import { GhostInput } from "@/components/soft-ledger/GhostInput";
import { kitchensMessages } from "@/lib/i18n/kitchens";
import type { Locale } from "@/lib/i18n/locale";
import { sidePanelMessages } from "@/lib/i18n/sidePanel";
import { requestSidePanelRefresh, setDefaultKitchen } from "@/lib/sidePanelClient";
import { shoppingListMessages } from "@/lib/i18n/shoppingList";
import { SectionLabel } from "@/components/soft-ledger/SectionLabel";
import { useKitchenCartCount } from "./cartCount";
import { InviteForm, type InviteFormMessages } from "./InviteForm";
import {
  archiveKitchen,
  deleteKitchen,
  memberLabel,
  renameKitchen,
  unarchiveKitchen,
  type KitchenMember,
} from "./kitchensClient";

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

/** The management actions in the header row (spec 064, contracts/side-panel-ui.md). */
export type KitchenManage = {
  kitchenId: string;
  name: string;
  isOwner: boolean;
  isArchived: boolean;
  isDefault: boolean;
  locale: Locale;
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
  manage?: KitchenManage;
};

type Action = {
  key: string;
  label: string;
  icon: ReactNode;
  danger?: boolean;
  onClick: () => void;
};

/** Opts kitchen detail into AppShell's title, the cart and share buttons and the kitchen actions. */
export function KitchenDetailChrome({ title, share, cart, manage }: Props) {
  const { push, refresh } = useRouter();
  const toast = useToast();
  const [open, setOpen] = useState(false);
  const [renaming, setRenaming] = useState(false);
  const [draft, setDraft] = useState("");
  const [deleting, setDeleting] = useState(false);
  const [pending, setPending] = useState(false);
  const [dialogError, setDialogError] = useState<string | null>(null);
  const locale = manage?.locale ?? cart?.locale ?? "en";
  const kt = kitchensMessages[locale];
  const panelText = sidePanelMessages[locale];
  const openLabel = share?.labels.open;
  const cartHref = cart?.href;
  const cartLabel = cart?.label;
  const cartLocale = cart?.locale;
  const cartCount = useKitchenCartCount();

  const actions = useMemo(() => {
    if (!manage) return [];
    const { kitchenId, name, isOwner, isArchived, isDefault } = manage;
    const fail = (text: string) => toast.show({ id: "kitchen-action", text });
    const list: Action[] = [];
    if (!isArchived && !isDefault) {
      list.push({
        key: "default",
        label: panelText.setDefault,
        icon: <StarIcon className="size-5" />,
        onClick: () =>
          void setDefaultKitchen(kitchenId).then((result) => {
            if (!result) return fail(kt.errorGeneric);
            requestSidePanelRefresh();
            refresh();
          }),
      });
    }
    if (!isOwner) return list;
    if (isArchived) {
      list.push({
        key: "restore",
        label: panelText.restore,
        icon: <ArchiveToggleIcon active className="size-5" />,
        onClick: () =>
          void unarchiveKitchen(kitchenId, kt).then((result) => {
            if (!result.ok) return fail(result.error);
            requestSidePanelRefresh();
            refresh();
          }),
      });
      return list;
    }
    list.push(
      {
        key: "rename",
        label: panelText.rename,
        icon: <PencilIcon className="size-5" />,
        onClick: () => {
          setDraft(name);
          setDialogError(null);
          setRenaming(true);
        },
      },
      {
        key: "archive",
        label: panelText.archive,
        icon: <ArchiveToggleIcon className="size-5" />,
        onClick: () =>
          void archiveKitchen(kitchenId, kt).then((result) => {
            if (!result.ok) return fail(result.error);
            requestSidePanelRefresh();
            push("/home");
          }),
      },
      {
        key: "delete",
        label: kt.deleteAria,
        icon: <TrashIcon className="size-5" />,
        danger: true,
        onClick: () => {
          setDialogError(null);
          setDeleting(true);
        },
      },
    );
    return list;
  }, [manage, kt, panelText, push, refresh, toast]);

  const trailing = useMemo(
    () =>
      openLabel || cartHref || actions.length > 0 ? (
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
          {actions.length > 0 ? (
            <span className="inline-flex">
              <IconButtonPopup
                panelRole="menu"
                button={
                  <IconButton
                    type="button"
                    variant="ghost"
                    label={kt.menuAria}
                    icon={<DotsIcon className="size-6" />}
                  />
                }
              >
                {actions.map((action) => (
                  <IconButtonPopupItem
                    key={action.key}
                    danger={action.danger}
                    onClick={action.onClick}
                  >
                    <span className="inline-flex items-center gap-2">
                      {action.icon}
                      {action.label}
                    </span>
                  </IconButtonPopupItem>
                ))}
              </IconButtonPopup>
            </span>
          ) : null}
        </>
      ) : undefined,
    [openLabel, cartHref, cartLabel, cartLocale, cartCount, push, actions, kt.menuAria],
  );

  useChromeHeader({
    title,
    trailing,
  });

  async function onRename() {
    if (!manage || pending) return;
    const name = draft.trim();
    if (!name) {
      setDialogError(kt.errorInvalidName);
      return;
    }
    setPending(true);
    const result = await renameKitchen(manage.kitchenId, name, kt);
    setPending(false);
    if (!result.ok) {
      setDialogError(result.error);
      return;
    }
    setRenaming(false);
    refresh();
  }

  async function onDelete() {
    if (!manage || pending) return;
    setPending(true);
    const result = await deleteKitchen(manage.kitchenId, kt);
    setPending(false);
    if (!result.ok) {
      setDialogError(result.error);
      return;
    }
    setDeleting(false);
    requestSidePanelRefresh();
    push("/home");
  }

  const errorLine = dialogError ? (
    <p className="m-0 mt-2 text-owe text-[0.85rem]" role="alert">
      {dialogError}
    </p>
  ) : null;

  const manageDialogs = manage ? (
    <>
      <ActionDialog
        open={renaming}
        title={panelText.rename}
        confirmLabel={panelText.renameSave}
        cancelLabel={kt.deleteCancel}
        onOpenChange={setRenaming}
        onConfirm={() => void onRename()}
        pending={pending}
      >
        <GhostInput
          aria-label={kt.renameAria}
          type="text"
          value={draft}
          maxLength={200}
          autoComplete="off"
          disabled={pending}
          onChange={(event) => setDraft(event.target.value)}
        />
        {errorLine}
      </ActionDialog>
      <ActionDialog
        open={deleting}
        title={kt.deleteAria}
        confirmLabel={pending ? kt.deletingAction : kt.deleteAction}
        cancelLabel={kt.deleteCancel}
        onOpenChange={setDeleting}
        onConfirm={() => void onDelete()}
        pending={pending}
      >
        <p className="m-0">{kt.deleteConfirm}</p>
        {errorLine}
      </ActionDialog>
    </>
  ) : null;

  if (!share) return manageDialogs;

  return (
    <>
    {manageDialogs}
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
    </>
  );
}
