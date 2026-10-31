"use client";

import { ActionDialog } from "@/components/ActionDialog";
import { GhostInput } from "@/components/soft-ledger/GhostInput";
import type { Locale } from "@/lib/i18n/locale";
import { kitchensMessages } from "@/lib/i18n/kitchens";
import { sidePanelMessages } from "@/lib/i18n/sidePanel";
import { useCreateKitchen } from "./useCreateKitchen";

/** The name dialog behind the panel's "+" and the no-kitchens prompt. */
export function CreateKitchenDialog({
  open,
  locale,
  onOpenChange,
  onCreated,
}: {
  open: boolean;
  locale: Locale;
  onOpenChange: (open: boolean) => void;
  onCreated?: () => void;
}) {
  const t = kitchensMessages[locale];
  const panel = sidePanelMessages[locale];
  const { name, setName, error, pending, submit } = useCreateKitchen(locale);

  async function onConfirm() {
    if (!(await submit())) return;
    onOpenChange(false);
    onCreated?.();
  }

  return (
    <ActionDialog
      open={open}
      title={panel.createTitle}
      confirmLabel={pending ? t.creating : t.createSubmit}
      cancelLabel={panel.createCancel}
      onOpenChange={onOpenChange}
      onConfirm={() => void onConfirm()}
      pending={pending}
    >
      <GhostInput
        aria-label={t.createLabel}
        placeholder={t.createLabel}
        type="text"
        value={name}
        maxLength={200}
        autoComplete="off"
        disabled={pending}
        onChange={(event) => setName(event.target.value)}
      />
      {error ? (
        <p className="m-0 mt-2 text-owe text-[0.85rem]" role="alert">
          {error}
        </p>
      ) : null}
    </ActionDialog>
  );
}
