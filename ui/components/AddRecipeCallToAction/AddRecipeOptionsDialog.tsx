"use client";

import { ActionDialog } from "@/components/ActionDialog/ActionDialog";
import { useCaptureMessages } from "@/lib/i18n/useCaptureMessages";

type AddRecipeOptionsDialogProps = {
  open: boolean;
  onClose: () => void;
  onChooseUrl: () => void;
  onChooseText: () => void;
};

const optionClassName =
  "flex w-full items-center justify-between gap-4 py-3 text-left text-[0.95rem] text-foreground";

/**
 * The add-recipe options (spec 016 FR-023): no confirm or cancel buttons, a vertical list
 * separated by dividers, in this order: URL, Picture, Text. URL opens the link sheet (spec 026);
 * Picture stays disabled until S-041.
 */
export function AddRecipeOptionsDialog({
  open,
  onClose,
  onChooseUrl,
  onChooseText,
}: AddRecipeOptionsDialogProps) {
  const t = useCaptureMessages();
  return (
    <ActionDialog
      open={open}
      title={t.addRecipe}
      onOpenChange={(next) => {
        if (!next) onClose();
      }}
    >
      <ul role="list" className="m-0 flex list-none flex-col divide-y divide-border p-0">
        <li>
          <button type="button" onClick={onChooseUrl} className={optionClassName}>
            <span>{t.optionUrl}</span>
          </button>
        </li>
        <li>
          <button type="button" aria-disabled="true" className={`${optionClassName} opacity-50`}>
            <span>{t.optionPicture}</span>
            <span className="text-[0.8rem] text-muted">{t.optionPictureNote}</span>
          </button>
        </li>
        <li>
          <button type="button" onClick={onChooseText} className={optionClassName}>
            <span>{t.optionText}</span>
          </button>
        </li>
      </ul>
    </ActionDialog>
  );
}
