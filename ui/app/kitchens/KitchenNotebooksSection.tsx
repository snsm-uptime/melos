"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { AddRecipeCallToAction } from "@/components/AddRecipeCallToAction";
import { NotebookCard } from "@/components/NotebookCard/NotebookCard";
import { RecipeList } from "@/components/RecipeList/RecipeList";
import { SavedNotice } from "@/components/RecipeDraft/SavedNotice";
import { SectionLabel } from "@/components/soft-ledger/SectionLabel";
import { listAddress, readListAddress } from "@/lib/listAddress";
import type { Locale } from "@/lib/i18n/locale";
import { notebooksMessages } from "@/lib/i18n/notebooks";
import {
  fetchKitchenNotebooks,
  type NotebookError,
  type NotebookResponse,
} from "@/lib/notebooksClient";
import { fetchKitchenRecipes } from "@/lib/recipesClient";

import styles from "../notebooks/notebooks.module.scss";

type KitchenNotebooksSectionProps = {
  kitchenId: string;
  /** An archived kitchen shows no add-recipe action (spec 016 FR-033). */
  isArchived: boolean;
  /** The signed-in person's alias. The owner line is hidden when the owner is this person. */
  viewerAlias: string | null;
  locale: Locale;
};

type SectionState =
  | { status: "loading" }
  | { status: "ready"; notebooks: NotebookResponse[] }
  | { status: "not_found" }
  | { status: "error" };

/** A kitchen's notebooks for its members, inert cards only (spec 060 FR-004 to FR-007). */
export function KitchenNotebooksSection({
  kitchenId,
  isArchived,
  viewerAlias,
  locale,
}: KitchenNotebooksSectionProps) {
  const t = notebooksMessages[locale];
  const router = useRouter();
  const pathname = usePathname();
  const { page, q } = readListAddress(useSearchParams());
  const [attempt, setAttempt] = useState(0);
  const [state, setState] = useState<SectionState>({ status: "loading" });

  useEffect(() => {
    let current = true;

    function fail(error: NotebookError) {
      if (error.code === "alias_required") {
        router.replace(`/alias?returnTo=${encodeURIComponent(`/kitchens/${kitchenId}`)}`);
        return;
      }
      if (error.code === "kitchen_not_found") {
        setState({ status: "not_found" });
        return;
      }
      setState({ status: "error" });
    }

    async function load() {
      const result = await fetchKitchenNotebooks(kitchenId);
      if (!current) return;
      if (!result.ok) {
        fail(result);
        return;
      }
      setState({ status: "ready", notebooks: result.value });
    }

    void load();
    return () => {
      current = false;
    };
  }, [attempt, kitchenId, router]);

  const onListChange = useCallback(
    (nextPage: number, nextQ: string) => router.replace(listAddress(pathname, nextPage, nextQ)),
    [pathname, router],
  );
  const loadRecipes = useCallback(
    (nextPage: number, nextQ: string) => fetchKitchenRecipes(kitchenId, nextPage, nextQ),
    [kitchenId],
  );

  function retry() {
    // Drop the previous list before the reload, so no stale cards stay on screen.
    setState({ status: "loading" });
    setAttempt((value) => value + 1);
  }

  return (
    <section className={styles.section}>
      <SectionLabel>{t.sectionTitle}</SectionLabel>
      <SavedNotice returnPath={`/kitchens/${kitchenId}`} />
      {state.status === "not_found" ? (
        <p className={styles.copy} role="alert">
          {t.detailNotFound}
        </p>
      ) : null}
      {state.status === "error" ? (
        <div className={styles.state}>
          <p className={styles.copy} role="alert">
            {t.loadError}
          </p>
          <button type="button" className={styles.retry} onClick={retry}>
            {t.retry}
          </button>
        </div>
      ) : null}
      {state.status === "ready" && state.notebooks.length === 0 ? (
        <p className={styles.copy}>{t.kitchenEmpty}</p>
      ) : null}
      {state.status === "ready" && state.notebooks.length > 0 && !isArchived ? (
        <AddRecipeCallToAction
          candidates={state.notebooks.map((notebook) => ({
            id: notebook.id,
            name: notebook.name,
            kind: "kitchen",
            kitchenId,
          }))}
          defaultId={state.notebooks[0]?.id ?? null}
          returnPath={`/kitchens/${kitchenId}`}
        />
      ) : null}
      {state.status === "ready" && state.notebooks.length > 0 ? (
        <ul className={styles.grid}>
          {state.notebooks.map((notebook) => (
            <li key={notebook.id}>
              <NotebookCard
                name={notebook.name}
                ownerAlias={notebook.owner_alias}
                viewerAlias={viewerAlias}
                locale={locale}
                href={`/notebooks/${notebook.id}`}
              />
            </li>
          ))}
        </ul>
      ) : null}
      {state.status === "ready" ? (
        <RecipeList
          scope="kitchen"
          locale={locale}
          page={page}
          q={q}
          onChange={onListChange}
          load={loadRecipes}
          returnPath={`/kitchens/${kitchenId}`}
        />
      ) : null}
    </section>
  );
}
