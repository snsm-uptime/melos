"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";

import { ShareIcon } from "@/app/icons";
import { useChromeHeader } from "@/components/ChromeBack";
import { IconButton } from "@/components/IconButton";
import { RecipeList } from "@/components/RecipeList/RecipeList";
import { SavedNotice } from "@/components/RecipeDraft/SavedNotice";
import { listAddress, readListAddress } from "@/lib/listAddress";
import type { Locale } from "@/lib/i18n/locale";
import { notebooksMessages } from "@/lib/i18n/notebooks";
import { recipeListMessages } from "@/lib/i18n/recipeLists";
import { fetchNotebook, type NotebookResponse } from "@/lib/notebooksClient";
import { notebookBackPath } from "@/lib/recipeReturnPath";
import { fetchNotebookRecipes } from "@/lib/recipesClient";

import { NotebookShareDialog } from "./NotebookShareDialog";
import styles from "../notebooks.module.scss";

type NotebookState =
  | { status: "loading" }
  | { status: "ready"; notebook: NotebookResponse }
  | { status: "not_found" }
  | { status: "error" };

/** One notebook's recipes as cards, with the text filter and numbered pages (spec 021). */
export function NotebookRecipesScreen({
  notebookId,
  locale,
}: {
  notebookId: string;
  locale: Locale;
}) {
  const t = recipeListMessages[locale];
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const { page, q } = readListAddress(searchParams);
  const backHref = notebookBackPath(searchParams.get("from"));
  const [state, setState] = useState<NotebookState>({ status: "loading" });
  const [sharing, setSharing] = useState(false);

  useEffect(() => {
    let current = true;
    void fetchNotebook(notebookId).then((result) => {
      if (!current) return;
      if (result.ok) setState({ status: "ready", notebook: result.value });
      else if (result.code === "alias_required") {
        router.replace(`/alias?returnTo=${encodeURIComponent(`/notebooks/${notebookId}`)}`);
      } else if (result.status === 404) {
        // Access ended or never existed: the person's notebooks are the way back (spec 057).
        setState({ status: "not_found" });
        router.replace("/notebooks");
      } else setState({ status: "error" });
    });
    return () => {
      current = false;
    };
  }, [notebookId, router]);

  // This list's own address keeps `?from=`, so a recipe opened from here returns to a list
  // whose Back still leads to the kitchen or tab the person came from.
  const listPath = searchParams.get("from")
    ? `${pathname}?from=${encodeURIComponent(searchParams.get("from") as string)}`
    : pathname;
  const onChange = useCallback(
    (nextPage: number, nextQ: string) => router.replace(listAddress(listPath, nextPage, nextQ)),
    [listPath, router],
  );
  const load = useCallback(
    async (nextPage: number, nextQ: string) => {
      const result = await fetchNotebookRecipes(notebookId, nextPage, nextQ);
      // A person removed while this list was open: the next page answers 404 (spec 057).
      if (!result.ok && result.status === 404) router.replace("/notebooks");
      return result;
    },
    [notebookId, router],
  );

  const returnPath = `/notebooks/${notebookId}`;
  // Personal notebooks only: a kitchen notebook's people come from the kitchen (spec 057 FR-003).
  const sharedPersonally = state.status === "ready" && state.notebook.kind === "personal";
  const shareLabel = notebooksMessages[locale].sharingOpen;
  const trailing = useMemo(
    () =>
      sharedPersonally ? (
        <IconButton
          type="button"
          variant="ghost"
          label={shareLabel}
          aria-haspopup="dialog"
          onClick={() => setSharing(true)}
          icon={<ShareIcon className="size-6" />}
        />
      ) : undefined,
    [shareLabel, sharedPersonally],
  );
  useChromeHeader({
    backHref,
    title: state.status === "ready" ? state.notebook.name : undefined,
    trailing,
  });
  const archived = state.status === "ready" && state.notebook.kitchen_is_archived === true;

  return (
    <main className={styles.main}>
      <SavedNotice returnPath={returnPath} />
      {state.status === "not_found" ? (
        <p className={styles.copy} role="alert">
          {t.notFoundNotebook}
        </p>
      ) : null}
      {state.status === "error" ? (
        <p className={styles.copy} role="alert">
          {t.loadError}
        </p>
      ) : null}
      {state.status === "ready" && state.notebook.origin_notebook_name ? (
        <p className={styles.copy}>
          {notebooksMessages[locale].originLabel(state.notebook.origin_notebook_name)}
        </p>
      ) : null}
      {state.status === "ready" ? (
        <RecipeList
          scope="notebook"
          locale={locale}
          page={page}
          q={q}
          onChange={onChange}
          load={load}
          returnPath={listPath}
          addCandidates={
            archived
              ? undefined
              : [
                  {
                    id: state.notebook.id,
                    name: state.notebook.name,
                    kind: state.notebook.kind,
                    kitchenId: state.notebook.kitchen_id,
                  },
                ]
          }
        />
      ) : null}
      {state.status === "ready" && state.notebook.kind === "personal" ? (
        <NotebookShareDialog
          open={sharing}
          onOpenChange={setSharing}
          notebookId={notebookId}
          isOwner={state.notebook.access === "owner"}
          locale={locale}
        />
      ) : null}
    </main>
  );
}
