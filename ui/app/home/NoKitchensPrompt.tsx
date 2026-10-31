"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { useChromeHeader } from "@/components/ChromeBack";
import { usePreferences } from "@/components/PreferencesProvider";
import { CreateKitchenDialog } from "@/components/SidePanel/CreateKitchenDialog";
import { PrimaryButton } from "@/components/soft-ledger/PrimaryButton";
import { kitchensMessages } from "@/lib/i18n/kitchens";
import { sidePanelMessages } from "@/lib/i18n/sidePanel";

/** Home for someone with no active kitchen; once one exists, the page redirects to it. */
export function NoKitchensPrompt() {
  const { locale } = usePreferences();
  const { refresh } = useRouter();
  const [open, setOpen] = useState(false);
  const t = kitchensMessages[locale];
  useChromeHeader({ title: t.title });
  return (
    <>
      <p className="m-0 text-muted">{sidePanelMessages[locale].noKitchens}</p>
      <div className="mt-4">
        <PrimaryButton type="button" onClick={() => setOpen(true)}>
          {t.createSubmit}
        </PrimaryButton>
      </div>
      <CreateKitchenDialog open={open} locale={locale} onOpenChange={setOpen} onCreated={refresh} />
    </>
  );
}
