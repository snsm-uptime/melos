"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { CauldronLoader } from "@/components/CauldronLoader";
import { useChromeHeader } from "@/components/ChromeBack";
import { NotebookCard } from "@/components/NotebookCard/NotebookCard";
import type { Locale } from "@/lib/i18n/locale";
import { notebooksMessages } from "@/lib/i18n/notebooks";
import { fetchKitchenNotebooks, type NotebookResponse } from "@/lib/notebooksClient";
import { requestSidePanelRefresh } from "@/lib/sidePanelClient";

import styles from "../notebooks/notebooks.module.scss";
import { AddNotebookSnapshot } from "./AddNotebookSnapshot";

type ScreenState =
  | { status: "loading" }
  | { status: "ready"; notebooks: NotebookResponse[] }
  | { status: "not_found" }
  | { status: "error" };

type KitchenNotebooksScreenProps = {
  kitchenId: string;
  locale: Locale;
  viewerAlias: string | null;
};

/**
 * The kitchen's notebooks as cards, in the Notebook tab's grid (spec 035 FR-007a). The first cell
 * adds a personal notebook. A kitchen that isn't archived always lists at least one notebook,
 * since the first read makes it, so an empty list also means no add action.
 */
export function KitchenNotebooksScreen({
  kitchenId,
  locale,
  viewerAlias,
}: KitchenNotebooksScreenProps) {
  const t = notebooksMessages[locale];
  const router = useRouter();
  const kitchenPath = `/kitchens/${encodeURIComponent(kitchenId)}`;
  useChromeHeader({ backHref: kitchenPath, title: t.sectionTitle });
  const [attempt, setAttempt] = useState(0);
  const [state, setState] = useState<ScreenState>({ status: "loading" });

  useEffect(() => {
    let current = true;
    void fetchKitchenNotebooks(kitchenId).then((result) => {
      if (!current) return;
      if (result.ok) {
        setState({ status: "ready", notebooks: result.value });
      } else if (result.code === "alias_required") {
        router.replace(`/alias?returnTo=${encodeURIComponent(`${kitchenPath}/notebooks`)}`);
      } else if (result.code === "kitchen_not_found") {
        setState({ status: "not_found" });
      } else {
        setState({ status: "error" });
      }
    });
    return () => {
      current = false;
    };
  }, [attempt, kitchenId, kitchenPath, router]);

  function reload() {
    setAttempt((value) => value + 1);
  }

  function retry() {
    setState({ status: "loading" });
    reload();
  }

  function onAdded() {
    reload();
    requestSidePanelRefresh();
  }

  const canAdd =
    state.status === "ready" &&
    state.notebooks.some((notebook) => notebook.kitchen_is_archived === false);
  const from = encodeURIComponent(`${kitchenPath}/notebooks`);

  return (
    <section className={`${styles.section} flex-1`}>
      {state.status === "loading" ? <CauldronLoader label={t.loading} /> : null}
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
      {state.status === "ready" && state.notebooks.length > 0 ? (
        <ul className={styles.grid}>
          {canAdd ? (
            <li>
              <AddNotebookSnapshot kitchenId={kitchenId} locale={locale} onAdded={onAdded} />
            </li>
          ) : null}
          {state.notebooks.map((notebook) => (
            <li key={notebook.id}>
              <NotebookCard
                name={notebook.name}
                ownerAlias={notebook.owner_alias}
                recipeCount={notebook.recipe_count}
                viewerAlias={viewerAlias}
                locale={locale}
                href={`/notebooks/${notebook.id}?from=${from}`}
              />
            </li>
          ))}
        </ul>
      ) : null}
    </section>
  );
}
