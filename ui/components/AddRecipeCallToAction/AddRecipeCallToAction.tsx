"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { AddRecipeIcon, PlusIcon } from "@/app/icons";
import { AddItemCard } from "@/components/Card";
import { IconButton } from "@/components/IconButton";
import { SidePanelEntry } from "@/components/SidePanel/SidePanelEntry";
import { useToast } from "@/components/Toast";
import { AccentButton } from "@/components/soft-ledger/AccentButton";
import {
  failSubmit,
  openSheet,
  startManualDraft,
  useCaptureState,
  type CaptureNotebook,
  type CaptureSource,
} from "@/lib/capture/captureStore";
import { useCaptureMessages } from "@/lib/i18n/useCaptureMessages";
import { useLocale } from "@/lib/i18n/useLocale";
import type { CopiedRecipe } from "@/lib/notebooksClient";

import { AddRecipeOptionsDialog } from "./AddRecipeOptionsDialog";
import { captureTarget, pickerOptions } from "./captureNotebook";
import { RecipeFromNotebookSheet } from "./RecipeFromNotebookSheet";
import { TextCaptureSheet } from "./TextCaptureSheet";
import { UrlCaptureSheet } from "./UrlCaptureSheet";
import { useFromNotebookTarget } from "./useFromNotebookTarget";

export type { FromNotebookTarget } from "./useFromNotebookTarget";

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
   * beside a list's filter; "icon" is a plus icon button; "panel" is a side panel row (quick add).
   */
  variant?: "placeholder" | "button" | "icon" | "panel";
  /**
   * The kitchen a "Recipe from another notebook" copy goes to. Omit it to use the open kitchen
   * of the address, or the member's kitchens to choose from.
   */
  kitchenId?: string | null;
  /**
   * The personal notebook whose page this add is on: the copy's original notebook, fixed.
   * Omit it (quick add, kitchen pages) and the person picks the original notebook.
   */
  sourceNotebookId?: string | null;
  /** After a copy, for example to reload the kitchen's list. */
  onCopied?: (copied: CopiedRecipe, kitchenId: string) => void;
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
  kitchenId,
  sourceNotebookId,
  onCopied,
  opener,
}: AddRecipeCallToActionProps) {
  const t = useCaptureMessages();
  const locale = useLocale();
  const router = useRouter();
  const toast = useToast();
  const capture = useCaptureState();
  const fromNotebook = useFromNotebookTarget(kitchenId);
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

  function preselectedNotebook(): CaptureNotebook | null {
    if (!preselected) return null;
    return {
      id: preselected.id,
      kind: preselected.kind,
      name: preselected.name,
      kitchenId: preselected.kitchenId,
      returnPath,
      opener,
    };
  }

  function choose(kind: CaptureSource["kind"]) {
    setOptionsOpen(false);
    const notebook = preselectedNotebook();
    if (notebook) openSheet(notebook, kind);
  }

  /** The empty form: into the preselected notebook, the kitchen's own made first if needed. */
  async function chooseManual() {
    setOptionsOpen(false);
    const notebook = preselectedNotebook();
    if (!notebook) return;
    const target = await captureTarget(notebook);
    if (!target.ok) {
      // Shown on the text sheet, as for a capture whose notebook cannot be made.
      openSheet(notebook, "text");
      failSubmit({ code: target.code });
      return;
    }
    startManualDraft(
      target.notebook,
      locale,
      pickerOptions(candidates, target.notebook).map(({ id, kind, name, kitchenId }) => ({
        id,
        kind,
        name,
        kitchenId,
      })),
    );
    goToDraft();
  }

  function copied(result: CopiedRecipe, kitchenId: string) {
    setFromNotebookOpen(false);
    toast.show({
      id: "recipe-copied",
      text: result.overwritten
        ? t.fromNotebookOverwritten(result.notebook_name)
        : t.fromNotebookAdded(result.notebook_name),
    });
    onCopied?.(result, kitchenId);
  }

  return (
    <>
      {variant === "panel" ? (
        <SidePanelEntry
          label={t.addRecipeButton}
          icon={<AddRecipeIcon className="size-7 shrink-0 p-0.5" />}
          disabled={!preselected}
          onClick={() => setOptionsOpen(true)}
        />
      ) : variant === "icon" ? (
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
        onChooseManual={() => void chooseManual()}
        onChooseFromNotebook={() => {
          setOptionsOpen(false);
          setFromNotebookKey((value) => value + 1);
          setFromNotebookOpen(true);
        }}
        fromNotebookDisabledReason={fromNotebook.disabledReason}
      />
      <RecipeFromNotebookSheet
        key={fromNotebookKey}
        open={fromNotebookOpen}
        onClose={() => setFromNotebookOpen(false)}
        sourceNotebookId={sourceNotebookId}
        kitchenId={fromNotebook.kitchenId}
        kitchenName={fromNotebook.kitchenName}
        kitchens={fromNotebook.kitchens}
        onDone={copied}
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
