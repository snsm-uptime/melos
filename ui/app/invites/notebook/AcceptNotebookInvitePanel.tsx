"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { CauldronLoader } from "@/components/CauldronLoader";
import { GhostButton } from "@/components/soft-ledger/GhostButton";
import { PrimaryButton } from "@/components/soft-ledger/PrimaryButton";
import { notebookInviteMessages, type Locale } from "@/lib/i18n/invite";
import {
  acceptNotebookInvite,
  fetchNotebookInvitePreview,
  type NotebookInvitePreview,
} from "../notebookInviteClient";
import styles from "../../signup/signup.module.scss";

type Props = {
  locale: Locale;
  token: string;
  authenticated: boolean;
};

type Stage =
  | { name: "working" }
  | { name: "preview"; preview: NotebookInvitePreview }
  | { name: "verify" }
  | { name: "refused"; code: string };

/**
 * The emailed link. Signed in, it joins on open with no button (FR-010). Signed out, it shows only
 * the safe preview, and a new person reopens the link after creating an account (research R8).
 */
export function AcceptNotebookInvitePanel({ locale, token, authenticated }: Props) {
  const router = useRouter();
  const t = notebookInviteMessages[locale];
  const [stage, setStage] = useState<Stage>({ name: "working" });
  const link = `/invites/notebook?token=${encodeURIComponent(token)}`;

  useEffect(() => {
    if (!token) return;
    let cancelled = false;
    (async () => {
      if (!authenticated) {
        const result = await fetchNotebookInvitePreview(token);
        if (cancelled) return;
        setStage(
          result.ok
            ? { name: "preview", preview: result.preview }
            : { name: "refused", code: result.code },
        );
        return;
      }
      const result = await acceptNotebookInvite(token);
      if (cancelled) return;
      if (result.ok) {
        router.replace(`/notebooks/${encodeURIComponent(result.notebookId)}`);
        router.refresh();
      } else if (result.code === "alias_required") {
        router.replace(`/alias?returnTo=${encodeURIComponent(link)}`);
      } else if (result.code === "email_not_verified") {
        setStage({ name: "verify" });
      } else {
        setStage({ name: "refused", code: result.code });
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [authenticated, link, router, token]);

  if (!token) {
    return (
      <p className={styles.error} role="alert">
        {t.errorExpired}
      </p>
    );
  }

  if (stage.name === "refused") {
    const message =
      stage.code === "invalid_invite_token"
        ? t.errorExpired
        : stage.code === "invite_email_mismatch"
          ? t.errorMismatch
          : t.errorGeneric;
    return (
      <p className={styles.error} role="alert">
        {message}
      </p>
    );
  }

  if (stage.name === "verify") {
    return (
      <div className={styles.form}>
        <p className={styles.error} role="alert">
          {t.errorNotVerified}
        </p>
        <PrimaryButton href={`/verify?returnTo=${encodeURIComponent(link)}`}>
          {t.verifyCta}
        </PrimaryButton>
      </div>
    );
  }

  if (stage.name === "preview") {
    const { notebook_name: name, inviter_alias: inviter, email_hint: hint } = stage.preview;
    return (
      <div className={styles.form}>
        <p className={styles.hint}>
          {inviter ? t.previewInvited(inviter, name) : t.previewNotebook(name)}
        </p>
        <p className={styles.hint}>{t.previewEmail(hint)}</p>
        <PrimaryButton href={`/sign-in?returnTo=${encodeURIComponent(link)}`}>
          {t.signInCta}
        </PrimaryButton>
        <GhostButton href="/signup">{t.createAccountCta}</GhostButton>
        <p className={styles.hint}>{t.reopenNote}</p>
      </div>
    );
  }

  return <CauldronLoader label={authenticated ? t.accepting : t.loading} />;
}
