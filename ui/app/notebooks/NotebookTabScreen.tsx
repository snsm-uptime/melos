"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { AddRecipeCallToAction } from "@/components/AddRecipeCallToAction";
import { ChromeAvatarLink } from "@/components/ChromeAvatarLink";
import { useChromeHeader } from "@/components/ChromeBack";
import { NotebookCard } from "@/components/NotebookCard/NotebookCard";
import { SavedNotice } from "@/components/RecipeDraft/SavedNotice";
import type { Locale } from "@/lib/i18n/locale";
import { notebooksMessages } from "@/lib/i18n/notebooks";
import {
  fetchDefaultNotebook,
  fetchPersonalNotebooks,
  type NotebookError,
  type NotebookResponse,
} from "@/lib/notebooksClient";

import styles from "./notebooks.module.scss";

/** Same target as `aliasSetupHref` in lib/alias, kept local so this client file never imports server code. */
const ALIAS_STEP_HREF = `/alias?returnTo=${encodeURIComponent("/notebooks")}`;

type TabState =
  | { status: "loading" }
  | { status: "ready"; defaultId: string; notebooks: NotebookResponse[] }
  | { status: "error" };

export function NotebookTabScreen({
  locale,
  viewerAlias,
  userId,
  photoBase64,
}: {
  locale: Locale;
  viewerAlias: string | null;
  userId: string;
  photoBase64: string | null;
}) {
  const t = notebooksMessages[locale];
  // A top-level tab root, like Home: the avatar leads and the title sits in the shared header.
  useChromeHeader({
    leading: <ChromeAvatarLink alias={viewerAlias} userId={userId} photoBase64={photoBase64} />,
    title: t.title,
  });
  const router = useRouter();
  const [attempt, setAttempt] = useState(0);
  const [state, setState] = useState<TabState>({ status: "loading" });

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

  return (
    <main className={styles.tabMain}>
      <SavedNotice returnPath="/notebooks" />
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
        <p className={styles.copy}>{t.tabEmpty}</p>
      ) : null}
      {state.status === "ready" && state.notebooks.length > 0 ? (
        <ul className={styles.grid}>
          {/* The first cell adds a recipe; the picker preselects the default notebook. */}
          <li>
            <AddRecipeCallToAction
              candidates={state.notebooks.map((notebook) => ({
                id: notebook.id,
                name: notebook.name,
                kind: "personal",
                kitchenId: null,
              }))}
              defaultId={state.defaultId}
              returnPath="/notebooks"
            />
          </li>
          {state.notebooks.map((notebook) => (
            <li key={notebook.id}>
              <NotebookCard
                name={notebook.name}
                ownerAlias={notebook.owner_alias}
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
    </main>
  );
}
