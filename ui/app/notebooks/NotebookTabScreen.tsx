"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { ChopsticksWokIcon, UserIcon } from "@/app/icons";
import { CauldronLoader } from "@/components/CauldronLoader";
import { useChromeHeader } from "@/components/ChromeBack";
import { NotebookCard } from "@/components/NotebookCard/NotebookCard";
import { SavedNotice } from "@/components/RecipeDraft/SavedNotice";
import { TabButton, TabList } from "@/components/Tabs";
import type { Locale } from "@/lib/i18n/locale";
import { notebooksMessages } from "@/lib/i18n/notebooks";
import {
  fetchDefaultNotebook,
  fetchPersonalNotebooks,
  type NotebookError,
  type NotebookResponse,
} from "@/lib/notebooksClient";

import { NewNotebookCard } from "./NewNotebookCard";
import styles from "./notebooks.module.scss";

/** Same target as `aliasSetupHref` in lib/alias, kept local so this client file never imports server code. */
const ALIAS_STEP_HREF = `/alias?returnTo=${encodeURIComponent("/notebooks")}`;

/** The notebook tab's two lists: the caller's personal notebooks, and the notebooks of their kitchens. */
type ListTab = "personal" | "kitchen";

type TabState =
  | { status: "loading" }
  | { status: "ready"; defaultId: string; notebooks: NotebookResponse[] }
  | { status: "error" };

export function NotebookTabScreen({
  locale,
  viewerAlias,
}: {
  locale: Locale;
  viewerAlias: string | null;
}) {
  const t = notebooksMessages[locale];
  // A top-level tab root, like Home: the avatar leads and the title sits in the shared header.
  useChromeHeader({
    title: t.title,
  });
  const router = useRouter();
  const [attempt, setAttempt] = useState(0);
  const [state, setState] = useState<TabState>({ status: "loading" });
  const [listTab, setListTab] = useState<ListTab>("personal");

  useEffect(() => {
    let current = true;

    // Step 2 runs only after step 1 succeeds, so a failed default never lists anything.
    function fail(error: NotebookError) {
      if (error.code === "alias_required") {
        router.replace(ALIAS_STEP_HREF);
        return;
      }
      setState({ status: "error" });
    }

    async function load() {
      const defaultResult = await fetchDefaultNotebook();
      if (!current) return;
      if (!defaultResult.ok) {
        fail(defaultResult);
        return;
      }

      const list = await fetchPersonalNotebooks();
      if (!current) return;
      if (!list.ok) {
        fail(list);
        return;
      }
      setState({ status: "ready", defaultId: defaultResult.value.id, notebooks: list.value });
    }

    void load();
    return () => {
      current = false;
    };
  }, [attempt, router]);

  function retry() {
    // Drop the previous list before the reload, so no stale cards stay on screen.
    setState({ status: "loading" });
    setAttempt((value) => value + 1);
  }

  const kindOfTab = listTab === "personal" ? "personal" : "kitchen";
  const shown = state.status === "ready" ? state.notebooks.filter((n) => n.kind === kindOfTab) : [];
  const emptyText = listTab === "personal" ? t.tabEmpty : t.tabKitchenEmpty;

  return (
    <main className={`${styles.tabMain} flex-1`}>
      <SavedNotice returnPath="/notebooks" />
      <TabList label={t.tabsLabel}>
        <TabButton
          id="notebook-tab-personal"
          selected={listTab === "personal"}
          onSelect={() => setListTab("personal")}
          icon={<UserIcon className="size-5" />}
          label={t.tabPersonal}
        />
        <TabButton
          id="notebook-tab-kitchen"
          selected={listTab === "kitchen"}
          onSelect={() => setListTab("kitchen")}
          icon={<ChopsticksWokIcon className="size-5" />}
          label={t.tabKitchen}
        />
      </TabList>
      <div role="tabpanel" aria-labelledby={`notebook-tab-${listTab}`} className={styles.tabPanel}>
        {state.status === "loading" ? <CauldronLoader label={t.loading} /> : null}
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
        {state.status === "ready" && listTab === "personal" ? (
          <ul className={styles.grid}>
            {/* The first cell makes a notebook; recipes are added inside a notebook. */}
            <li>
              <NewNotebookCard locale={locale} />
            </li>
            {shown.map((notebook) => (
              <li key={notebook.id}>
                <NotebookCard
                  name={notebook.name}
                  ownerAlias={notebook.owner_alias}
                  recipeCount={notebook.recipe_count}
                  access={notebook.access}
                  isDefault={notebook.is_default}
                  viewerAlias={viewerAlias}
                  locale={locale}
                  href={`/notebooks/${notebook.id}`}
                />
              </li>
            ))}
          </ul>
        ) : null}
        {state.status === "ready" && listTab === "personal" && shown.length === 0 ? (
          <p className={styles.copy}>{emptyText}</p>
        ) : null}
        {state.status === "ready" && listTab === "kitchen" && shown.length > 0 ? (
          <ul className={styles.grid}>
            {shown.map((notebook) => (
              <li key={notebook.id}>
                <NotebookCard
                  name={notebook.name}
                  kind="kitchen"
                  ownerAlias={notebook.owner_alias}
                  recipeCount={notebook.recipe_count}
                  viewerAlias={viewerAlias}
                  locale={locale}
                  href={`/notebooks/${notebook.id}`}
                />
              </li>
            ))}
          </ul>
        ) : null}
        {state.status === "ready" && listTab === "kitchen" && shown.length === 0 ? (
          <p className={styles.copy}>{emptyText}</p>
        ) : null}
      </div>
    </main>
  );
}

