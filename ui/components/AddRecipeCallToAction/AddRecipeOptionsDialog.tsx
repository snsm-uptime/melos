"use client";

import { ActionDialog } from "@/components/ActionDialog/ActionDialog";
import { captureMessages } from "@/lib/i18n/capture";

type AddRecipeOptionsDialogProps = {
  open: boolean;
  onClose: () => void;
  onChooseText: () => void;
};

const optionClassName =
  "flex w-full items-center justify-between gap-4 py-3 text-left text-[0.95rem] text-foreground";

/**
 * The add-recipe options (spec 016 FR-023): no confirm or cancel buttons, a vertical list
 * separated by dividers, in this order: URL, Picture, Text. Only Text works in this feature.
 */
export function AddRecipeOptionsDialog({ open, onClose, onChooseText }: AddRecipeOptionsDialogProps) {
  return (
    <ActionDialog
      open={open}
      title={captureMessages.addRecipe}
      onOpenChange={(next) => {
        if (!next) onClose();
      }}
    >
      <ul role="list" className="m-0 flex list-none flex-col divide-y divide-border p-0">
        <li>
          <button type="button" aria-disabled="true" className={`${optionClassName} opacity-50`}>
            <span>{captureMessages.optionUrl}</span>
            <span className="text-[0.8rem] text-muted">{captureMessages.optionUrlNote}</span>
          </button>
        </li>
        <li>
          <button type="button" aria-disabled="true" className={`${optionClassName} opacity-50`}>
            <span>{captureMessages.optionPicture}</span>
            <span className="text-[0.8rem] text-muted">{captureMessages.optionPictureNote}</span>
          </button>
        </li>
        <li>
          <button type="button" onClick={onChooseText} className={optionClassName}>
            <span>{captureMessages.optionText}</span>
          </button>
        </li>
      </ul>
    </ActionDialog>
  );
}
