"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { PlusIcon } from "@/app/icons";
import { AddItemCard } from "@/components/Card";
import { AccentButton } from "@/components/soft-ledger/AccentButton";
import {
  openSheet,
  useCaptureState,
  type CaptureNotebook,
  type CaptureSource,
} from "@/lib/capture/captureStore";
import { useCaptureMessages } from "@/lib/i18n/useCaptureMessages";

import { AddRecipeOptionsDialog } from "./AddRecipeOptionsDialog";
import { TextCaptureSheet } from "./TextCaptureSheet";
import { UrlCaptureSheet } from "./UrlCaptureSheet";

export type CaptureCandidate = {
  id: string;
  name: string;
  kind: "personal" | "kitchen";
  kitchenId: string | null;
};

type AddRecipeCallToActionProps = {
  /** Notebooks the member may capture into: the picker's choices (spec 016 FR-001a). */
  candidates: CaptureCandidate[];
  /** Preselected in the picker (the default personal notebook; the member's own kitchen one). */
  defaultId: string | null;
  /** The page that opened the capture. Back and Discard return here. */
  returnPath: string;
  /**
   * "placeholder" is the rounded plus tile; "button" is a compact labelled button that sits
   * beside a list's filter.
   */
  variant?: "placeholder" | "button";
};

/**
 * The shared add-recipe call to action (AGENTS.md): a rounded placeholder with a plus icon.
 * Tapping it opens the options dialog; URL opens the link sheet and Text the text sheet, for the
 * chosen notebook (specs 016 and 026).
 */
export function AddRecipeCallToAction({
  candidates,
  defaultId,
  returnPath,
  variant = "placeholder",
}: AddRecipeCallToActionProps) {
  const t = useCaptureMessages();
  const router = useRouter();
  const capture = useCaptureState();
  const [optionsOpen, setOptionsOpen] = useState(false);

  const preselected = candidates.find((item) => item.id === defaultId) ?? candidates[0];
  const sheetOpen = capture.sheetOpen && capture.notebook?.returnPath === returnPath;
  const goToDraft = () => router.push("/notebooks/draft");

  function choose(kind: CaptureSource["kind"]) {
    setOptionsOpen(false);
    if (!preselected) return;
    const notebook: CaptureNotebook = {
      id: preselected.id,
      kind: preselected.kind,
      name: preselected.name,
      kitchenId: preselected.kitchenId,
      returnPath,
    };
    openSheet(notebook, kind);
  }

  return (
    <>
      {variant === "button" ? (
        <AccentButton
          type="button"
          onClick={() => setOptionsOpen(true)}
          disabled={!preselected}
          iconLeft={<PlusIcon className="size-4" />}
          className="shrink-0 whitespace-nowrap"
        >
          {t.addRecipeButton}
        </AccentButton>
      ) : (
        // Fills its grid row so it matches the card beside it; never shorter than the shortest
        // NotebookCard (one title line, the recipe count, its padding and border).
        <AddItemCard
          label={t.addRecipe}
          onClick={() => setOptionsOpen(true)}
          disabled={!preselected}
          className="h-full"
        />
      )}
      <AddRecipeOptionsDialog
        open={optionsOpen}
        onClose={() => setOptionsOpen(false)}
        onChooseUrl={() => choose("url")}
        onChooseText={() => choose("text")}
      />
      <TextCaptureSheet
        open={sheetOpen && capture.source.kind === "text"}
        candidates={candidates}
        onDraftReady={goToDraft}
      />
      <UrlCaptureSheet
        open={sheetOpen && capture.source.kind === "url"}
        candidates={candidates}
        onDraftReady={goToDraft}
      />
    </>
  );
}
