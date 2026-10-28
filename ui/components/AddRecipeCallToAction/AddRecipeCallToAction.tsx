"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { PlusIcon } from "@/app/icons";
import { openSheet, useCaptureState, type CaptureNotebook } from "@/lib/capture/captureStore";
import { useCaptureMessages } from "@/lib/i18n/useCaptureMessages";

import { AddRecipeOptionsDialog } from "./AddRecipeOptionsDialog";
import { TextCaptureSheet } from "./TextCaptureSheet";

export type CaptureCandidate = {
  id: string;
  name: string;
  kind: "personal" | "kitchen";
  kitchenId: string | null;
};

type AddRecipeCallToActionProps = {
  /** Notebooks the member may capture into: the picker's choices (spec 016 FR-001a). */
  candidates: CaptureCandidate[];
  /** Preselected in the picker (the default personal notebook; the kitchen's first notebook). */
  defaultId: string | null;
  /** The page that opened the capture. Back and Discard return here. */
  returnPath: string;
};

/**
 * The shared add-recipe call to action (AGENTS.md): a rounded placeholder with a plus icon.
 * Tapping it opens the options dialog; Text opens the text sheet for the chosen notebook.
 */
export function AddRecipeCallToAction({ candidates, defaultId, returnPath }: AddRecipeCallToActionProps) {
  const t = useCaptureMessages();
  const router = useRouter();
  const capture = useCaptureState();
  const [optionsOpen, setOptionsOpen] = useState(false);

  const preselected = candidates.find((item) => item.id === defaultId) ?? candidates[0];
  const sheetOpen = capture.sheetOpen && capture.notebook?.returnPath === returnPath;

  function chooseText() {
    setOptionsOpen(false);
    if (!preselected) return;
    const notebook: CaptureNotebook = {
      id: preselected.id,
      kind: preselected.kind,
      name: preselected.name,
      kitchenId: preselected.kitchenId,
      returnPath,
    };
    openSheet(notebook);
  }

  return (
    <>
      <button
        type="button"
        aria-label={t.addRecipe}
        onClick={() => setOptionsOpen(true)}
        disabled={!preselected}
        className="flex h-[7.5rem] w-full items-center justify-center rounded-[1.25rem] border border-dashed border-border bg-surface text-muted"
      >
        <PlusIcon />
      </button>
      <AddRecipeOptionsDialog
        open={optionsOpen}
        onClose={() => setOptionsOpen(false)}
        onChooseText={chooseText}
      />
      <TextCaptureSheet
        open={sheetOpen}
        candidates={candidates}
        onDraftReady={() => router.push("/notebooks/draft")}
      />
    </>
  );
}
