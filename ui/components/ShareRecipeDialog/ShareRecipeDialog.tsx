"use client";

import { useEffect, useRef, useState } from "react";

import { SendIcon } from "@/app/icons";
import { ActionDialog } from "@/components/ActionDialog";
import { SearchableSelect } from "@/components/SearchableSelect";
import type { Locale } from "@/lib/i18n/locale";
import { messagesFor } from "@/lib/i18n/messages";
import { recipeShareMessages } from "@/lib/i18n/recipeShare";
import {
  listShareCandidates,
  shareRecipe,
  type ShareCandidate,
} from "@/lib/recipeShareClient";

type ShareRecipeDialogProps = {
  recipeId: string;
  locale: Locale;
  open: boolean;
  onOpenChange: (open: boolean) => void;
};

type SendState = "idle" | "sending" | "sent";

/**
 * Pick a co-member and send them a copy of the recipe (spec 071). Only people who share a
 * kitchen or a notebook are listed; the server checks the same rule on send. One press sends
 * once: the button is disabled from the first press until the answer comes back (research R-4).
 */
export function ShareRecipeDialog({
  recipeId,
  locale,
  open,
  onOpenChange,
}: ShareRecipeDialogProps) {
  const t = messagesFor(recipeShareMessages, locale);
  // null while loading; an empty list is a valid answer.
  const [candidates, setCandidates] = useState<ShareCandidate[] | null>(null);
  const [loadFailed, setLoadFailed] = useState(false);
  const [chosen, setChosen] = useState("");
  const [sendState, setSendState] = useState<SendState>("idle");
  const [sentAlias, setSentAlias] = useState("");
  const [error, setError] = useState<string | null>(null);
  const sendingRef = useRef(false);

  useEffect(() => {
    if (!open) return;
    let cancelled = false;
    // The parent mounts this dialog only while it is open, so the state starts fresh.
    listShareCandidates().then((list) => {
      if (cancelled) return;
      if (list === null) setLoadFailed(true);
      setCandidates(list ?? []);
    });
    return () => {
      cancelled = true;
    };
  }, [open]);

  function errorText(code: string | null): string {
    switch (code) {
      case "recipe_not_found":
        return t.shareErrorRecipeNotFound;
      case "recipient_not_found":
        return t.shareErrorRecipientNotFound;
      case "share_self":
        return t.shareErrorSelf;
      case "recipient_no_default_notebook":
        return t.shareErrorNoDefault;
      default:
        return t.shareErrorGeneric;
    }
  }

  async function send() {
    if (sendingRef.current || !chosen) return;
    sendingRef.current = true;
    setSendState("sending");
    setError(null);
    const result = await shareRecipe(recipeId, chosen);
    sendingRef.current = false;
    if (result.ok) {
      const alias =
        result.recipientAlias ||
        candidates?.find((c) => c.user_id === chosen)?.alias ||
        "";
      setSentAlias(alias);
      setSendState("sent");
      return;
    }
    // The chosen person stays selected so the member can fix the problem and send again.
    setError(errorText(result.code));
    setSendState("idle");
  }

  const options = (candidates ?? []).map((c) => ({
    value: c.user_id,
    label: c.alias,
  }));
  const sent = sendState === "sent";

  return (
    <ActionDialog
      open={open}
      title={t.shareTitle}
      closeLabel={t.shareClose}
      onOpenChange={onOpenChange}
    >
      {sent ? (
        <p role="status" className="m-0 text-foreground">
          {t.shareSent(sentAlias)}
        </p>
      ) : candidates === null ? (
        <p className="m-0 text-muted">{t.shareLoading}</p>
      ) : options.length === 0 ? (
        <p className="m-0 text-muted">
          {loadFailed ? t.shareErrorGeneric : t.shareNoCandidates}
        </p>
      ) : (
        <div className="flex flex-col gap-2">
          <div className="flex w-full max-w-full items-center gap-1 rounded-[var(--radius-md)] border border-border bg-surface py-1 pr-1 pl-2 [&>span]:min-w-0 [&>span]:flex-1">
            <SearchableSelect
              className="min-w-0 flex-1 justify-between text-[0.95rem] text-foreground"
              aria-label={t.shareSearchLabel}
              placeholder={t.sharePlaceholder}
              searchLabel={t.shareSearchLabel}
              noResults={t.shareNoResults}
              value={chosen}
              disabled={sendState === "sending"}
              options={options}
              onChange={(value) => {
                setChosen(value);
                setError(null);
              }}
              action={{
                icon: <SendIcon className="size-4" />,
                label: t.shareSend,
                onClick: () => void send(),
                disabled: !chosen || sendState !== "idle",
              }}
            />
          </div>
          {error ? (
            <p role="alert" className="m-0 text-[0.9rem] text-error">
              {error}
            </p>
          ) : null}
        </div>
      )}
    </ActionDialog>
  );
}
