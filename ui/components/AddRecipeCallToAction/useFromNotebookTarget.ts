"use client";

import { usePathname } from "next/navigation";

import { useMembershipKitchens } from "@/app/kitchens/membershipKitchensStore";
import { useCaptureMessages } from "@/lib/i18n/useCaptureMessages";

import type { KitchenChoice } from "./RecipeFromNotebookSheet";

/** "Recipe from another notebook" (spec 069): where the copy goes. */
export type FromNotebookTarget = {
  /** The kitchen the copy goes to, used without asking. */
  kitchenId?: string | null;
  /** The name of that kitchen, shown in place of a choice. */
  kitchenName?: string | null;
  /** Outside a kitchen: the active kitchens to choose from. */
  kitchens?: KitchenChoice[];
  /** Shows the option disabled with this reason. */
  disabledReason?: string | null;
};

/** The open kitchen of a `/kitchens/{id}…` address, or null elsewhere. */
export function kitchenFromPath(pathname: string): string | null {
  const match = /^\/kitchens\/([^/?#]+)/.exec(pathname);
  return match ? decodeURIComponent(match[1]) : null;
}

/**
 * Where "Recipe from another notebook" copies to, the same on every add-recipe entry point:
 * the kitchen the caller names, else the open kitchen of the address, else the member's active
 * kitchens to choose from. An archived kitchen takes no recipes, so the option stays visible but
 * disabled there.
 */
export function useFromNotebookTarget(kitchenHint?: string | null): FromNotebookTarget {
  const t = useCaptureMessages();
  const pathname = usePathname() ?? "";
  const kitchens = useMembershipKitchens();
  const kitchenId = kitchenHint ?? kitchenFromPath(pathname);

  if (kitchenId) {
    const kitchen = kitchens?.find((item) => item.id === kitchenId);
    if (kitchen?.is_archived) return { kitchenId, disabledReason: t.fromNotebookArchived };
    return { kitchenId, kitchenName: kitchen?.name ?? null };
  }
  const active = (kitchens ?? [])
    .filter((item) => !item.is_archived)
    .map((item) => ({ id: item.id, name: item.name }));
  return {
    kitchens: active,
    disabledReason: kitchens && active.length === 0 ? t.fromNotebookNoKitchen : null,
  };
}
