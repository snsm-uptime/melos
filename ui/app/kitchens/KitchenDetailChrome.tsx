"use client";

import { useMemo, useState } from "react";

import { ShareIcon } from "@/app/icons";
import { ActionDialog } from "@/components/ActionDialog";
import { Avatar } from "@/components/Avatar";
import { useChromeHeader } from "@/components/ChromeBack";
import { IconButton } from "@/components/IconButton";
import { SectionLabel } from "@/components/soft-ledger/SectionLabel";
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
};

/** Opts kitchen detail into AppShell Back + title, and the owner's share button. */
export function KitchenDetailChrome({ title, share }: Props) {
  const [open, setOpen] = useState(false);
  const openLabel = share?.labels.open;

  const trailing = useMemo(
    () =>
      openLabel ? (
        <IconButton
          type="button"
          variant="ghost"
          label={openLabel}
          aria-haspopup="dialog"
          onClick={() => setOpen(true)}
          icon={<ShareIcon className="size-6" />}
        />
      ) : undefined,
    [openLabel],
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
