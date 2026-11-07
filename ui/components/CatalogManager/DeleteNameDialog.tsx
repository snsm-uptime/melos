"use client";

import { useState } from "react";

import { ActionDialog } from "@/components/ActionDialog";
import { deleteName, type CatalogIngredient } from "@/lib/catalogClient";
import type { CatalogMessages } from "@/lib/i18n/catalog";

const LINK =
  "self-start text-[0.9rem] text-accent underline-offset-2 hover:underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent";

/**
 * Delete a name no recipe uses (spec 043 US3, FR-013). A used name is refused with the number
 * of recipes and a "Merge instead" button.
 */
export function DeleteNameDialog({
  t,
  notebookId,
  ingredient,
  onClose,
  onDone,
  onMergeInstead,
  onChanged,
}: {
  t: CatalogMessages;
  notebookId: string;
  ingredient: CatalogIngredient;
  onClose: () => void;
  onDone: (message: string) => void;
  onMergeInstead: () => void;
  onChanged: () => void;
}) {
  // Known before asking: the catalog says how many recipes use the name.
  const [inUse, setInUse] = useState<number>(ingredient.recipe_count);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function remove() {
    if (pending) return;
    setPending(true);
    setError(null);
    const result = await deleteName(notebookId, ingredient.name);
    setPending(false);
    if (result.ok) onDone(t.deleted(ingredient.name));
    else if (result.code === "name_in_use") setInUse(result.recipe_count ?? 1);
    else if (result.code === "name_changed") onChanged();
    else setError(t.saveError);
  }

  return (
    <ActionDialog
      open
      title={t.deleteTitle(ingredient.name)}
      confirmLabel={inUse > 0 ? undefined : t.deleteConfirm}
      cancelLabel={t.cancel}
      pending={pending}
      onOpenChange={(open) => {
        if (!open) onClose();
      }}
      onConfirm={() => void remove()}
    >
      <div className="flex flex-col gap-3">
        <p className="m-0 text-[0.95rem] text-foreground">
          {inUse > 0 ? t.inUse(inUse) : t.deleteBody}
        </p>
        {inUse > 0 ? (
          <button type="button" className={LINK} onClick={onMergeInstead}>
            {t.mergeInstead}
          </button>
        ) : null}
        {error ? (
          <p className="m-0 text-[0.9rem] text-muted" role="alert">
            {error}
          </p>
        ) : null}
      </div>
    </ActionDialog>
  );
}
