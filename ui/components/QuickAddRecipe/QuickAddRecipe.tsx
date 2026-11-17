"use client";

import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

import { useMembershipKitchens } from "@/app/kitchens/membershipKitchensStore";
import {
  AddRecipeCallToAction,
  type CaptureCandidate,
} from "@/components/AddRecipeCallToAction";
import { kitchenFromPath } from "@/components/AddRecipeCallToAction/useFromNotebookTarget";
import { OWN_NEW_NOTEBOOK_ID } from "@/lib/capture/captureStore";
import { notebooksMessages } from "@/lib/i18n/notebooks";
import { useLocale } from "@/lib/i18n/useLocale";
import {
  fetchDefaultNotebook,
  fetchPersonalNotebooks,
  type NotebookResponse,
} from "@/lib/notebooksClient";

type Target = { candidates: CaptureCandidate[]; defaultId: string | null };

export { kitchenFromPath };

/**
 * The side panel's quick add (spec 069 US2): the add-recipe options from any signed-in page, plus
 * Recipe from another notebook. Captures may go to any notebook the member can add to: their
 * personal notebooks and the notebooks of every active kitchen, grouped and labelled (spec 076
 * FR-008). Inside an active kitchen, its group comes first and captures default to the member's
 * own notebook there; elsewhere, to the default personal notebook. The copy targets the kitchen
 * whose pages are open, or asks which active kitchen.
 */
export function QuickAddRecipe() {
  const pathname = usePathname() ?? "";
  const locale = useLocale();
  const kitchens = useMembershipKitchens();
  const pathKitchen = kitchenFromPath(pathname);
  const kitchen = pathKitchen ? kitchens?.find((item) => item.id === pathKitchen) : undefined;
  // An archived kitchen takes no recipes: quick add acts as it does outside a kitchen there.
  const kitchenId = pathKitchen && !kitchen?.is_archived ? pathKitchen : null;
  // The roster gives the kitchens' order and names; labels refresh once it loads.
  const roster = (kitchens ?? []).map((item) => `${item.id}:${item.name}`).join(",");
  // Keyed by what it was read for, so a newer kitchen reads as not loaded yet (no reset).
  const targetKey = `${kitchenId}|${locale}|${roster}`;
  const [answer, setAnswer] = useState<{ key: string; value: Target | null } | null>(null);
  const target = answer?.key === targetKey ? answer.value : null;

  useEffect(() => {
    let current = true;
    async function load(): Promise<Target | null> {
      const t = notebooksMessages[locale];
      const listed = await fetchPersonalNotebooks();
      const rows = listed.ok ? listed.value : [];
      let personal = rows.filter((notebook) => notebook.kind === "personal");
      if (personal.length === 0) {
        // The default notebook is made on first use, as the Notebook tab does.
        const made = await fetchDefaultNotebook();
        personal = made.ok ? [made.value] : [];
      }

      // Each active kitchen's notebooks, in the roster's order, this page's kitchen first.
      const byKitchen = new Map<string, NotebookResponse[]>();
      for (const notebook of rows) {
        if (notebook.kind !== "kitchen" || !notebook.kitchen_id) continue;
        if (notebook.kitchen_is_archived === true) continue;
        byKitchen.set(notebook.kitchen_id, [...(byKitchen.get(notebook.kitchen_id) ?? []), notebook]);
      }
      if (kitchenId && !byKitchen.has(kitchenId)) byKitchen.set(kitchenId, []);
      const rank = (id: string) => {
        if (id === kitchenId) return -1;
        const index = kitchens?.findIndex((item) => item.id === id) ?? -1;
        return index === -1 ? Number.MAX_SAFE_INTEGER : index;
      };
      const kitchenIds = [...byKitchen.keys()].sort((a, b) => rank(a) - rank(b));

      const own = kitchenId
        ? byKitchen.get(kitchenId)!.find((notebook) => notebook.is_own_capture_notebook)
        : undefined;
      const groups: { label: string; items: CaptureCandidate[] }[] = kitchenIds.map((id) => {
        const items: CaptureCandidate[] = byKitchen.get(id)!.map((notebook) => ({
          id: notebook.id,
          name: notebook.name,
          kind: "kitchen",
          kitchenId: id,
        }));
        // Only this page's kitchen offers a notebook made on first capture (research R7).
        if (id === kitchenId && !own) {
          items.unshift({ id: OWN_NEW_NOTEBOOK_ID, name: t.ownNotebookNew, kind: "kitchen", kitchenId: id });
        }
        const label = kitchens?.find((item) => item.id === id)?.name ?? t.kitchenFallback;
        return { label, items };
      });
      const personalGroup = {
        label: t.personalGroup,
        items: personal.map<CaptureCandidate>((notebook) => ({
          id: notebook.id,
          name: notebook.name,
          kind: "personal",
          kitchenId: null,
        })),
      };
      // Personal notebooks come first, after this page's kitchen when there is one.
      groups.splice(kitchenId ? 1 : 0, 0, personalGroup);
      const offered = groups.filter((group) => group.items.length > 0);
      // Labels and dividers only when there is more than one group: a member with personal
      // notebooks only sees the picker as before.
      const candidates =
        offered.length > 1
          ? offered.flatMap((group, index) =>
              group.items.map((item, row) => ({
                ...item,
                detail: group.label,
                ...(index > 0 && row === 0 ? { dividerBefore: true } : {}),
              })),
            )
          : offered.flatMap((group) => group.items);

      if (kitchenId) return { candidates, defaultId: own?.id ?? OWN_NEW_NOTEBOOK_ID };
      return {
        candidates,
        defaultId:
          personal.find((notebook) => notebook.is_default)?.id ??
          personal[0]?.id ??
          candidates[0]?.id ??
          null,
      };
    }
    void load().then((next) => {
      if (current) setAnswer({ key: targetKey, value: next });
    });
    return () => {
      current = false;
    };
    // `kitchens` is read through `targetKey`, which changes with the roster's ids and names.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [kitchenId, locale, targetKey]);

  return (
    <AddRecipeCallToAction
      variant="panel"
      opener="quick-add"
      candidates={target?.candidates ?? []}
      defaultId={target?.defaultId ?? null}
      returnPath={pathname}
    />
  );
}
