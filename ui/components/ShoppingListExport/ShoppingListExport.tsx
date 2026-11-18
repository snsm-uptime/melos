"use client";

import { useEffect, useState } from "react";

import { shoppingExportMessages } from "@/lib/i18n/shoppingExport";
import { useLocale } from "@/lib/i18n/useLocale";

import { fetchExportPdf, fetchExportText, hasItems } from "./exportText";

const BUTTON =
  "inline-flex min-h-11 items-center justify-center rounded-[var(--radius-md)] border border-border bg-surface px-4 text-[0.95rem] text-foreground focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent disabled:opacity-50";

type ShoppingListExportProps = { kitchenId: string; listId: string };

/**
 * The export of one shopping list (spec 024): the Markdown in a copy box, and a PDF download.
 * It reads the saved list only; a PDF failure leaves the copy box working (AC5.5).
 */
export function ShoppingListExport({
  kitchenId,
  listId,
}: ShoppingListExportProps) {
  const t = shoppingExportMessages[useLocale()];
  const [text, setText] = useState<string | null | "error">(null);
  const [attempt, setAttempt] = useState(0);
  const [copied, setCopied] = useState(false);
  const [pdfBusy, setPdfBusy] = useState(false);
  const [pdfFailed, setPdfFailed] = useState(false);

  useEffect(() => {
    let current = true;
    void fetchExportText(kitchenId, listId).then((result) => {
      if (current) setText(result.ok ? result.value : "error");
    });
    return () => {
      current = false;
    };
  }, [kitchenId, listId, attempt]);

  const items = typeof text === "string" && hasItems(text);

  function retry() {
    setText(null);
    setAttempt((n) => n + 1);
  }

  async function copy() {
    if (typeof text !== "string") return;
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
    } catch {
      setCopied(false);
    }
  }

  async function downloadPdf() {
    setPdfBusy(true);
    setPdfFailed(false);
    const result = await fetchExportPdf(kitchenId, listId);
    setPdfBusy(false);
    if (!result.ok) {
      setPdfFailed(true);
      return;
    }
    const url = URL.createObjectURL(result.value.blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = result.value.fileName;
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 0);
  }

  return (
    <section
      aria-labelledby="shopping-export-title"
      className="flex flex-col gap-3 px-4"
    >
      <h2
        id="shopping-export-title"
        className="m-0 text-[1.05rem] font-[600] text-foreground"
      >
        {t.title}
      </h2>
      {text === null ? (
        <p className="m-0 text-[0.9rem] text-muted">{t.loading}</p>
      ) : text === "error" ? (
        <div className="flex flex-col items-start gap-2">
          <p className="m-0 text-[0.9rem] text-muted" role="alert">
            {t.loadError}
          </p>
          <button type="button" className={BUTTON} onClick={retry}>
            {t.retry}
          </button>
        </div>
      ) : (
        <>
          <textarea
            readOnly
            aria-label={t.copyBox}
            value={text}
            rows={Math.min(12, text.split("\n").length)}
            className="w-full rounded-[var(--radius-md)] border border-border bg-surface p-3 font-mono text-[0.85rem] text-foreground"
          />
          {items ? null : (
            <p className="m-0 text-[0.9rem] text-muted">{t.emptyHint}</p>
          )}
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              className={BUTTON}
              disabled={!items}
              onClick={() => void copy()}
            >
              {t.copy}
            </button>
            <button
              type="button"
              className={BUTTON}
              disabled={!items || pdfBusy}
              onClick={() => void downloadPdf()}
            >
              {t.downloadPdf}
            </button>
          </div>
          <p role="status" className="m-0 text-[0.9rem] text-muted">
            {copied ? t.copied : null}
          </p>
          {pdfFailed ? (
            <p className="m-0 text-[0.9rem] text-muted" role="alert">
              {t.pdfError}
            </p>
          ) : null}
        </>
      )}
    </section>
  );
}
