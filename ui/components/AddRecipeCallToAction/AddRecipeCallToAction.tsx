"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { PlusIcon } from "@/app/icons";
import { AddItemCard } from "@/components/Card";
import { IconButton } from "@/components/IconButton";
import { useToast } from "@/components/Toast";
import { AccentButton } from "@/components/soft-ledger/AccentButton";
import {
  openSheet,
  useCaptureState,
  type CaptureNotebook,
  type CaptureSource,
} from "@/lib/capture/captureStore";
import { useCaptureMessages } from "@/lib/i18n/useCaptureMessages";
import type { CopiedRecipe } from "@/lib/notebooksClient";

import { AddRecipeOptionsDialog } from "./AddRecipeOptionsDialog";
import { RecipeFromNotebookSheet, type KitchenChoice } from "./RecipeFromNotebookSheet";
import { TextCaptureSheet } from "./TextCaptureSheet";
import { UrlCaptureSheet } from "./UrlCaptureSheet";

export type CaptureCandidate = {
  id: string;
  name: string;
  kind: "personal" | "kitchen";
  kitchenId: string | null;
};

/** "Recipe from another notebook" (spec 069): where the copy goes. */
export type FromNotebookTarget = {
  /** The open kitchen; used without asking. */
  kitchenId?: string | null;
  /** Outside a kitchen: the active kitchens to choose from. */
  kitchens?: KitchenChoice[];
  /** Shows the option disabled with this reason (no active kitchen). */
  disabledReason?: string | null;
  /** After a copy, for example to reload the kitchen's list. */
  onCopied?: (copied: CopiedRecipe, kitchenId: string) => void;
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
   * beside a list's filter; "icon" is the plus icon button of the app header (quick add).
   */
  variant?: "placeholder" | "button" | "icon";
  /** Adds "Recipe from another notebook" to the options; absent on personal notebooks. */
  fromNotebook?: FromNotebookTarget;
  /** Tells this action's captures apart from another one on the same page (quick add). */
  opener?: string;
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
  fromNotebook,
  opener,
}: AddRecipeCallToActionProps) {
  const t = useCaptureMessages();
  const router = useRouter();
  const toast = useToast();
  const capture = useCaptureState();
  const [optionsOpen, setOptionsOpen] = useState(false);
  const [fromNotebookOpen, setFromNotebookOpen] = useState(false);
  // A new key per open, so the picker starts fresh each time.
  const [fromNotebookKey, setFromNotebookKey] = useState(0);

  const preselected = candidates.find((item) => item.id === defaultId) ?? candidates[0];
  const sheetOpen =
    capture.sheetOpen &&
    capture.notebook?.returnPath === returnPath &&
    capture.notebook?.opener === opener;
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
      opener,
    };
    openSheet(notebook, kind);
  }

  function copied(result: CopiedRecipe, kitchenId: string) {
    setFromNotebookOpen(false);
    toast.show({
      id: "recipe-copied",
      text: result.overwritten
        ? t.fromNotebookOverwritten(result.notebook_name)
        : t.fromNotebookAdded(result.notebook_name),
    });
    fromNotebook?.onCopied?.(result, kitchenId);
  }

  return (
    <>
      {variant === "icon" ? (
        <IconButton
          variant="ghost"
          label={t.addRecipeButton}
          aria-haspopup="dialog"
          icon={<PlusIcon className="size-6" />}
          onClick={() => setOptionsOpen(true)}
          disabled={!preselected}
        />
      ) : variant === "button" ? (
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
        onChooseFromNotebook={
          fromNotebook
            ? () => {
                setOptionsOpen(false);
                setFromNotebookKey((value) => value + 1);
                setFromNotebookOpen(true);
              }
            : undefined
        }
        fromNotebookDisabledReason={fromNotebook?.disabledReason}
      />
      {fromNotebook ? (
        <RecipeFromNotebookSheet
          key={fromNotebookKey}
          open={fromNotebookOpen}
          onClose={() => setFromNotebookOpen(false)}
          kitchenId={fromNotebook.kitchenId}
          kitchens={fromNotebook.kitchens}
          onDone={copied}
        />
      ) : null}
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
