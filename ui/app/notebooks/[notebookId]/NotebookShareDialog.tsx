"use client";

import { useRouter } from "next/navigation";
import { FormEvent, useCallback, useEffect, useId, useState } from "react";

import { ActionDialog } from "@/components/ActionDialog";
import { Avatar } from "@/components/Avatar";
import { FormIconField } from "@/components/FormIconSubmit";
import { GhostButton } from "@/components/soft-ledger/GhostButton";
import { SectionLabel } from "@/components/soft-ledger/SectionLabel";
import type { Locale } from "@/lib/i18n/locale";
import { notebooksMessages } from "@/lib/i18n/notebooks";
import {
  cancelNotebookInvite,
  fetchNotebookInvites,
  fetchNotebookMembers,
  inviteToNotebook,
  leaveNotebook,
  removeNotebookMember,
  resendNotebookInvite,
  type NotebookError,
  type NotebookInvite,
  type NotebookMember,
} from "@/lib/notebooksClient";

import styles from "../notebooks.module.scss";

type Confirming =
  | { kind: "leave" }
  | { kind: "remove"; member: NotebookMember }
  | { kind: "cancel"; invite: NotebookInvite };

type Notice = { kind: "status" | "alert"; text: string };

type Props = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  notebookId: string;
  /** Only the owner invites and removes; a member sees the people and can leave (spec 057). */
  isOwner: boolean;
  locale: Locale;
};

/**
 * Who is in a personal notebook and, for the owner, its invites: the kitchen's share dialog, opened
 * from the same place at the end of the chrome. A confirmation replaces the dialog's content,
 * because ActionDialog does not nest.
 */
export function NotebookShareDialog({ open, onOpenChange, notebookId, isOwner, locale }: Props) {
  const t = notebooksMessages[locale];
  const router = useRouter();
  const emailId = useId();
  const [members, setMembers] = useState<NotebookMember[] | null>(null);
  const [invites, setInvites] = useState<NotebookInvite[]>([]);
  const [failed, setFailed] = useState(false);
  const [notice, setNotice] = useState<Notice | null>(null);
  const [email, setEmail] = useState("");
  const [sending, setSending] = useState(false);
  const [confirming, setConfirming] = useState<Confirming | null>(null);
  const [acting, setActing] = useState(false);

  /** True when the failure was handled by leaving the page: access has ended. */
  const leftBecauseGone = useCallback(
    (error: NotebookError): boolean => {
      if (error.status === 404 && error.code === "notebook_not_found") {
        router.replace("/notebooks");
        return true;
      }
      return false;
    },
    [router],
  );

  const load = useCallback(async () => {
    const [people, open] = await Promise.all([
      fetchNotebookMembers(notebookId),
      isOwner ? fetchNotebookInvites(notebookId) : null,
    ]);
    if (!people.ok) {
      if (!leftBecauseGone(people)) setFailed(true);
      return;
    }
    if (open && !open.ok) {
      if (!leftBecauseGone(open)) setFailed(true);
      return;
    }
    setFailed(false);
    setMembers(people.value);
    setInvites(open?.ok ? open.value : []);
  }, [isOwner, leftBecauseGone, notebookId]);

  useEffect(() => {
    if (!open) return;
    let current = true;
    void Promise.resolve().then(() => (current ? load() : undefined));
    return () => {
      current = false;
    };
  }, [load, open]);

  function close(next: boolean) {
    if (next) return;
    if (confirming) {
      setConfirming(null);
      return;
    }
    setNotice(null);
    onOpenChange(false);
  }

  function problem(error: NotebookError): string {
    switch (error.code) {
      case "already_in_notebook":
        return t.sharingAlreadyIn;
      case "invalid_invite_email":
        return t.sharingInvalidEmail;
      case "smtp_config_error":
      case "smtp_send_error":
        return t.sharingEmailFailed;
      case "notebook_invite_not_found":
        return t.sharingInviteGone;
      case "notebook_member_not_found":
        return t.sharingMemberGone;
      default:
        return t.sharingFailed;
    }
  }

  async function onInvite(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const address = email.trim();
    if (!address || sending) return;
    setSending(true);
    setNotice(null);
    const result = await inviteToNotebook(notebookId, address);
    setSending(false);
    if (result.ok) {
      setEmail("");
      setNotice({ kind: "status", text: t.sharingSent(result.value.email) });
      await load();
    } else if (!leftBecauseGone(result)) {
      setNotice({ kind: "alert", text: problem(result) });
    }
  }

  async function onResend(invite: NotebookInvite) {
    setNotice(null);
    const result = await resendNotebookInvite(notebookId, invite.id);
    if (result.ok) {
      setNotice({ kind: "status", text: t.sharingSent(invite.email) });
      await load();
    } else if (!leftBecauseGone(result)) {
      setNotice({ kind: "alert", text: problem(result) });
      await load();
    }
  }

  const alias = (member: NotebookMember) => member.alias ?? t.ownerUnknown;

  async function onConfirm() {
    if (!confirming) return;
    setActing(true);
    setNotice(null);
    const result =
      confirming.kind === "leave"
        ? await leaveNotebook(notebookId)
        : confirming.kind === "remove"
          ? await removeNotebookMember(notebookId, confirming.member.user_id)
          : await cancelNotebookInvite(notebookId, confirming.invite.id);
    setActing(false);
    setConfirming(null);
    if (result.ok) {
      if (confirming.kind === "leave") {
        router.replace("/notebooks");
        return;
      }
      setNotice({
        kind: "status",
        text:
          confirming.kind === "remove"
            ? t.sharingRemoved(alias(confirming.member))
            : t.sharingCancelled(confirming.invite.email),
      });
      await load();
    } else if (!leftBecauseGone(result)) {
      setNotice({ kind: "alert", text: problem(result) });
      await load();
    }
  }

  const expiry = (invite: NotebookInvite) =>
    invite.expired
      ? t.sharingExpired
      : t.sharingExpires(new Date(invite.expires_at).toLocaleDateString(locale));

  const asking: { title: string; body: string; confirm: string } | null = !confirming
    ? null
    : confirming.kind === "leave"
      ? { title: t.sharingLeaveTitle, body: t.sharingLeaveBody, confirm: t.sharingLeaveConfirm }
      : confirming.kind === "remove"
        ? {
            title: t.sharingRemoveTitle(alias(confirming.member)),
            body: t.sharingRemoveBody,
            confirm: t.sharingRemoveConfirm,
          }
        : {
            title: t.sharingCancelTitle,
            body: t.sharingCancelBody(confirming.invite.email),
            confirm: t.sharingCancelConfirm,
          };

  // The key remounts the dialog when its content swaps, so focus moves to the new buttons
  // instead of being lost with the button that was pressed.
  return (
    <ActionDialog
      key={asking ? "confirm" : "people"}
      open={open}
      title={asking?.title ?? (isOwner ? t.sharingInvite : t.sharingPeople)}
      confirmLabel={asking?.confirm}
      cancelLabel={asking ? t.sharingKeep : t.sharingClose}
      onOpenChange={close}
      onConfirm={() => void onConfirm()}
      pending={acting}
    >
      {asking ? (
        <p className={styles.copy}>{asking.body}</p>
      ) : (
        <div className="flex flex-col gap-[var(--space-4)]">
          <div aria-live="polite">
            {notice ? (
              <p
                className={notice.kind === "alert" ? styles.alert : styles.copy}
                role={notice.kind}
              >
                {notice.text}
              </p>
            ) : null}
          </div>

          {isOwner ? (
            <form onSubmit={onInvite}>
              <FormIconField
                id={emailId}
                label={t.sharingEmailLabel}
                submitLabel={sending ? t.sharingSending : t.sharingSend}
                variant="send"
                type="email"
                name="email"
                autoComplete="email"
                inputMode="email"
                placeholder="person@home.com"
                required
                value={email}
                disabled={sending}
                submitDisabled={sending || email.trim().length === 0}
                onChange={(event) => setEmail(event.target.value)}
              />
            </form>
          ) : null}

          {isOwner && invites.length > 0 ? (
            <section className="flex flex-col gap-[var(--space-2)]">
              <SectionLabel>{t.sharingOpenInvites}</SectionLabel>
              <ul className={styles.rows}>
                {invites.map((invite) => (
                  <li className={styles.row} key={invite.id}>
                    <span className={styles.rowText}>
                      <span className={styles.rowName}>{invite.email}</span>
                      <span className={styles.copy}>{expiry(invite)}</span>
                    </span>
                    <span className={styles.rowActions}>
                      <GhostButton
                        aria-label={t.sharingResendLabel(invite.email)}
                        onClick={() => void onResend(invite)}
                      >
                        {t.sharingResend}
                      </GhostButton>
                      <GhostButton
                        aria-label={t.sharingCancelLabel(invite.email)}
                        onClick={() => setConfirming({ kind: "cancel", invite })}
                      >
                        {t.sharingCancel}
                      </GhostButton>
                    </span>
                  </li>
                ))}
              </ul>
            </section>
          ) : null}

          <section className="flex flex-col gap-[var(--space-2)]">
            <SectionLabel>{t.sharingPeople}</SectionLabel>
            {failed ? (
              <p className={styles.alert} role="alert">
                {t.sharingLoadError}
              </p>
            ) : (
              <ul className="m-0 flex max-h-[40vh] list-none flex-col gap-[var(--space-2)] overflow-y-auto p-0">
                {(members ?? []).map((member) => (
                  <li key={member.user_id} className="flex items-center gap-[var(--space-2)]">
                    <Avatar alias={member.alias} seed={member.user_id} />
                    <span className={styles.rowName}>{alias(member)}</span>
                    {member.role === "owner" ? (
                      <span className="text-[0.85rem] text-muted">{t.accessOwner}</span>
                    ) : null}
                    {member.is_self ? (
                      <span className="text-[0.85rem] text-muted">{t.sharingYou}</span>
                    ) : null}
                    {isOwner && member.role !== "owner" ? (
                      <span className="ml-auto">
                        <GhostButton
                          aria-label={t.sharingRemoveLabel(alias(member))}
                          onClick={() => setConfirming({ kind: "remove", member })}
                        >
                          {t.sharingRemoveConfirm}
                        </GhostButton>
                      </span>
                    ) : null}
                  </li>
                ))}
              </ul>
            )}
            {!isOwner ? (
              <div>
                <GhostButton onClick={() => setConfirming({ kind: "leave" })}>
                  {t.sharingLeave}
                </GhostButton>
              </div>
            ) : null}
          </section>
        </div>
      )}
    </ActionDialog>
  );
}
