"use client";

import { useCallback, useState, type ReactNode } from "react";

import { ShareIcon, CloseIcon } from "@/app/icons";
import { IconButton } from "@/components/IconButton";
import type { InviteFormMessages } from "./InviteForm";
import { InviteForm } from "./InviteForm";
import styles from "./TemporalNavigation.module.scss";

type FormKind = "invite" | null;

type Props = {
  kitchenId: string;
  isOwner: boolean;
  inviteMessages: InviteFormMessages;
};

type FormWrapperProps = {
  title: string;
  onClose: () => void;
  /** Content for the top-left of the form header (e.g. save icon), matching Sheet.cornerAction */
  cornerAction?: ReactNode;
  children: ReactNode;
};

function FormWrapper({ title, onClose, cornerAction, children }: FormWrapperProps) {
  return (
    <div className={styles.formContainer}>
      <div className={styles.formHeader}>
        {cornerAction ? <div className={styles.formLeading}>{cornerAction}</div> : null}
        <h3 className={styles.formTitle}>{title}</h3>
        <IconButton
          type="button"
          className={styles.formClose}
          label={`Close ${title}`}
          onClick={onClose}
          icon={<CloseIcon className={styles.closeIcon} />}
        />
      </div>
      <div className={styles.formBody}>{children}</div>
    </div>
  );
}

export function TemporalNavigation({ kitchenId, isOwner, inviteMessages }: Props) {
  const [openForm, setOpenForm] = useState<FormKind>(null);

  const handleClose = useCallback(() => {
    setOpenForm(null);
  }, []);

  // Invite is the only member action today, and it is owner-only.
  if (!isOwner) return null;

  return (
    <div className={styles.chrome}>
      {openForm === null ? (
        <div className={styles.navGroup} role="group">
          <IconButton
            type="button"
            className={styles.navButton}
            label="Share / Invite"
            onClick={() => setOpenForm("invite")}
            icon={<ShareIcon className={styles.navIcon} />}
          />
        </div>
      ) : null}

      {openForm === "invite" ? (
        <FormWrapper title={inviteMessages.inviteTitle} onClose={handleClose}>
          <InviteForm kitchenId={kitchenId} messages={inviteMessages} reserveErrorHeight />
        </FormWrapper>
      ) : null}
    </div>
  );
}
