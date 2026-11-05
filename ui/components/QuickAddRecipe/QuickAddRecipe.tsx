"use client";

import { usePathname } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { useMembershipKitchens } from "@/app/kitchens/membershipKitchensStore";
import {
  AddRecipeCallToAction,
  type CaptureCandidate,
  type FromNotebookTarget,
} from "@/components/AddRecipeCallToAction";
import { OWN_NEW_NOTEBOOK_ID } from "@/lib/capture/captureStore";
import { notebooksMessages } from "@/lib/i18n/notebooks";
import { useCaptureMessages } from "@/lib/i18n/useCaptureMessages";
import { useLocale } from "@/lib/i18n/useLocale";
import {
  fetchDefaultNotebook,
  fetchKitchenNotebooks,
  fetchPersonalNotebooks,
} from "@/lib/notebooksClient";

type Target = { candidates: CaptureCandidate[]; defaultId: string | null };

/** The open kitchen of a `/kitchens/{id}…` address, or null elsewhere. */
export function kitchenFromPath(pathname: string): string | null {
  const match = /^\/kitchens\/([^/?#]+)/.exec(pathname);
  return match ? decodeURIComponent(match[1]) : null;
}

/**
 * The side panel's quick add (spec 069 US2): the add-recipe options from any signed-in page, plus
 * Recipe from another notebook. Inside an active kitchen, captures default to the member's own
 * kitchen notebook and the copy targets that kitchen; elsewhere, captures go to the default
 * personal notebook and the copy asks which active kitchen.
 */
export function QuickAddRecipe() {
  const pathname = usePathname() ?? "";
  const locale = useLocale();
  const t = useCaptureMessages();
  const kitchens = useMembershipKitchens();
  const pathKitchen = kitchenFromPath(pathname);
  const kitchen = pathKitchen ? kitchens?.find((item) => item.id === pathKitchen) : undefined;
  // An archived kitchen takes no recipes: quick add acts as it does outside a kitchen there.
  const kitchenId = pathKitchen && !kitchen?.is_archived ? pathKitchen : null;
  const archivedHere = Boolean(pathKitchen && kitchen?.is_archived);
  // Keyed by what it was read for, so a newer kitchen reads as not loaded yet (no reset).
  const targetKey = `${kitchenId}|${locale}`;
  const [answer, setAnswer] = useState<{ key: string; value: Target | null } | null>(null);
  const target = answer?.key === targetKey ? answer.value : null;

  useEffect(() => {
    let current = true;
    async function load(): Promise<Target | null> {
      if (kitchenId) {
        const result = await fetchKitchenNotebooks(kitchenId);
        if (!result.ok) return null;
        const own = result.value.find((notebook) => notebook.is_own_capture_notebook);
        const candidates: CaptureCandidate[] = result.value.map((notebook) => ({
          id: notebook.id,
          name: notebook.name,
          kind: "kitchen",
          kitchenId,
        }));
        if (!own) {
          candidates.unshift({
            id: OWN_NEW_NOTEBOOK_ID,
            name: notebooksMessages[locale].ownNotebookNew,
            kind: "kitchen",
            kitchenId,
          });
        }
        return { candidates, defaultId: own?.id ?? OWN_NEW_NOTEBOOK_ID };
      }
      const listed = await fetchPersonalNotebooks();
      let personal = listed.ok ? listed.value.filter((n) => n.kind === "personal") : [];
      if (personal.length === 0) {
        // The default notebook is made on first use, as the Notebook tab does.
        const made = await fetchDefaultNotebook();
        personal = made.ok ? [made.value] : [];
      }
      return {
        candidates: personal.map((notebook) => ({
          id: notebook.id,
          name: notebook.name,
          kind: "personal",
          kitchenId: null,
        })),
        defaultId: personal.find((notebook) => notebook.is_default)?.id ?? personal[0]?.id ?? null,
      };
    }
    void load().then((next) => {
      if (current) setAnswer({ key: targetKey, value: next });
    });
    return () => {
      current = false;
    };
  }, [kitchenId, locale, targetKey]);

  const fromNotebook = useMemo<FromNotebookTarget | undefined>(() => {
    if (archivedHere) return undefined;
    if (kitchenId) return { kitchenId };
    const active = (kitchens ?? [])
      .filter((item) => !item.is_archived)
      .map((item) => ({ id: item.id, name: item.name }));
    return {
      kitchens: active,
      disabledReason: active.length === 0 ? t.fromNotebookNoKitchen : null,
    };
  }, [archivedHere, kitchenId, kitchens, t.fromNotebookNoKitchen]);

  return (
    <AddRecipeCallToAction
      variant="panel"
      opener="quick-add"
      candidates={target?.candidates ?? []}
      defaultId={target?.defaultId ?? null}
      returnPath={pathname}
      fromNotebook={fromNotebook}
    />
  );
}
