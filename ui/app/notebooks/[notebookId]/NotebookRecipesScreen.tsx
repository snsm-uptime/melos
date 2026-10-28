"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { RecipeList } from "@/components/RecipeList/RecipeList";
import { SavedNotice } from "@/components/RecipeDraft/SavedNotice";
import { listAddress, readListAddress } from "@/lib/listAddress";
import type { Locale } from "@/lib/i18n/locale";
import { recipeListMessages } from "@/lib/i18n/recipeLists";
import { fetchNotebook, type NotebookResponse } from "@/lib/notebooksClient";
import { fetchNotebookRecipes } from "@/lib/recipesClient";

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
  const { page, q } = readListAddress(useSearchParams());
  const [state, setState] = useState<NotebookState>({ status: "loading" });

  useEffect(() => {
    let current = true;
    void fetchNotebook(notebookId).then((result) => {
      if (!current) return;
      if (result.ok) setState({ status: "ready", notebook: result.value });
      else if (result.code === "alias_required") {
        router.replace(`/alias?returnTo=${encodeURIComponent(`/notebooks/${notebookId}`)}`);
      } else if (result.status === 404) setState({ status: "not_found" });
      else setState({ status: "error" });
    });
    return () => {
      current = false;
    };
  }, [notebookId, router]);

  const onChange = useCallback(
    (nextPage: number, nextQ: string) => router.replace(listAddress(pathname, nextPage, nextQ)),
    [pathname, router],
  );
  const load = useCallback(
    (nextPage: number, nextQ: string) => fetchNotebookRecipes(notebookId, nextPage, nextQ),
    [notebookId],
  );

  const returnPath = `/notebooks/${notebookId}`;
  const archived = state.status === "ready" && state.notebook.kitchen_is_archived === true;

  return (
    <main className={styles.main}>
      <h1 className={styles.title}>{state.status === "ready" ? state.notebook.name : ""}</h1>
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
      {state.status === "ready" ? (
        <RecipeList
          scope="notebook"
          locale={locale}
          page={page}
          q={q}
          onChange={onChange}
          load={load}
          returnPath={returnPath}
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
    </main>
  );
}
