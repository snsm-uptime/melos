"use client";

import { NotebookPicker } from "@/components/NotebookPicker";
import { useEffect, useState } from "react";

import type { Locale } from "@/lib/i18n/locale";
import { notebooksMessages } from "@/lib/i18n/notebooks";
import { sidePanelMessages } from "@/lib/i18n/sidePanel";
import {
  fetchDefaultNotebook,
  fetchPersonalNotebooks,
  setDefaultNotebook,
  type NotebookResponse,
} from "@/lib/notebooksClient";

/**
 * The default personal notebook, chosen from a searchable list of the caller's personal
 * notebooks. Loads the first time `active` is true (the Settings entry is open).
 */
export function DefaultNotebookField({
  active,
  locale,
}: {
  active: boolean;
  locale: Locale;
}) {
  const t = sidePanelMessages[locale];
  const notebookText = notebooksMessages[locale];
  const [notebooks, setNotebooks] = useState<NotebookResponse[]>([]);
  const [defaultId, setDefaultId] = useState<string>("");
  const [loaded, setLoaded] = useState(false);
  const [loadFailed, setLoadFailed] = useState(false);
  const [saveFailed, setSaveFailed] = useState(false);

  useEffect(() => {
    if (!active || loaded) return;
    let current = true;
    void Promise.all([fetchDefaultNotebook(), fetchPersonalNotebooks()]).then(
      ([def, list]) => {
        if (!current) return;
        if (!def.ok || !list.ok) {
          setLoadFailed(true);
          return;
        }
        setDefaultId(def.value.id);
        setNotebooks(
          list.value.filter((notebook) => notebook.kind === "personal"),
        );
        setLoaded(true);
      },
    );
    return () => {
      current = false;
    };
  }, [active, loaded]);

  async function choose(id: string) {
    const previous = defaultId;
    setDefaultId(id);
    setSaveFailed(false);
    const result = await setDefaultNotebook(id);
    if (!result.ok) {
      setDefaultId(previous);
      setSaveFailed(true);
      return;
    }
    setDefaultId(result.value.id);
  }

  return (
    <>
      {loadFailed ? (
        <p className="m-0 text-[0.8rem] text-error" role="alert">
          {notebookText.loadError}
        </p>
      ) : (
        <NotebookPicker
          locale={locale}
          label={t.defaultNotebook}
          value={defaultId}
          disabled={!loaded}
          notebooks={notebooks}
          onChange={(id) => void choose(id)}
        />
      )}
      {saveFailed ? (
        <p className="m-0 text-[0.8rem] text-error" role="alert">
          {t.defaultNotebookError}
        </p>
      ) : null}
    </>
  );
}
