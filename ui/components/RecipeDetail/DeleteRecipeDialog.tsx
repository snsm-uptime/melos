"use client";

import { useRef, useState } from "react";

import { ActionDialog } from "@/components/ActionDialog/ActionDialog";
import type { Locale } from "@/lib/i18n/locale";
import { recipeDetailMessages } from "@/lib/i18n/recipeDetail";
import { deleteRecipe } from "@/lib/recipesClient";

type DeleteRecipeDialogProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  recipeId: string;
  title: string;
  locale: Locale;
  /** The recipe is gone (deleted now, or already deleted elsewhere): leave the page. */
  onDeleted: () => void;
};

/** Confirm, then delete (spec 027 FR-013, FR-017). A second press sends no second request. */
export function DeleteRecipeDialog({
  open,
  onOpenChange,
  recipeId,
  title,
  locale,
  onDeleted,
}: DeleteRecipeDialogProps) {
  const t = recipeDetailMessages[locale];
  const [pending, setPending] = useState(false);
  const [problem, setProblem] = useState<string | null>(null);
  const sending = useRef(false);

  async function confirm() {
    if (sending.current) return;
    sending.current = true;
    setPending(true);
    setProblem(null);
    const result = await deleteRecipe(recipeId);
    sending.current = false;
    setPending(false);
    // Already deleted elsewhere counts as done: the member ends where they wanted to be.
    if (result.ok || result.status === 404) {
      onDeleted();
      return;
    }
    setProblem(result.status === 403 ? t.readOnly : t.deleteFailed);
  }

  return (
    <ActionDialog
      open={open}
      title={t.deleteTitle(title)}
      confirmLabel={pending ? t.deleting : t.deleteConfirm}
      cancelLabel={t.cancel}
      onOpenChange={(next) => {
        if (!pending) {
          setProblem(null);
          onOpenChange(next);
        }
      }}
      onConfirm={() => void confirm()}
      pending={pending}
    >
      <p className="m-0 text-foreground">{t.deleteBody}</p>
      {problem ? (
        <p className="mt-3 text-owe" role="alert">
          {problem}
        </p>
      ) : null}
    </ActionDialog>
  );
}
