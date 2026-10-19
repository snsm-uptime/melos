"use client";

import { useCallback, useRef, useState } from "react";

import { ShareIcon } from "@/app/icons";
import type { InviteFormMessages } from "./InviteForm";
import { InviteForm } from "./InviteForm";
import { Sheet } from "./Sheet";
import { IconButton } from "@/components/IconButton";
import styles from "./KitchenDetailMobileActions.module.scss";

type Props = {
  kitchenId: string;
  canInvite: boolean;
  inviteMessages: InviteFormMessages;
  inviteAria: string;
  closeLabel: string;
};

/**
 * Mobile-only kitchen actions. Hidden from md up — the sidebar owns the same
 * forms there. Sheets portal to document.
 */
export function KitchenDetailMobileActions({
  kitchenId,
  canInvite,
  inviteMessages,
  inviteAria,
  closeLabel,
}: Props) {
  const [open, setOpen] = useState(false);
  const close = useCallback(() => setOpen(false), []);
  const inviteButtonRef = useRef<HTMLButtonElement>(null);

  if (!canInvite) return null;

  return (
    <div className={styles.chrome}>
      <div className={styles.cluster} role="group" aria-label={inviteAria}>
        <IconButton
          ref={inviteButtonRef}
          type="button"
          variant="ghost"
          label={inviteAria}
          aria-expanded={open}
          onClick={() => setOpen(true)}
          icon={<ShareIcon className={styles.icon} />}
        />
      </div>

      <Sheet
        open={open}
        title={inviteMessages.inviteTitle}
        onClose={close}
        closeLabel={closeLabel}
        returnFocusRef={inviteButtonRef}
        body={
          <InviteForm
            kitchenId={kitchenId}
            messages={inviteMessages}
            reserveErrorHeight
            hideBorder
          />
        }
      />
    </div>
  );
}
