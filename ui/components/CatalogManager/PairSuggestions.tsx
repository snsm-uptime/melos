"use client";

import { useState } from "react";

import { CheckIcon, CloseIcon } from "@/app/icons";
import { CauldronLoader } from "@/components/CauldronLoader";
import { IconButton } from "@/components/IconButton";
import { GhostButton } from "@/components/soft-ledger/GhostButton";
import { dismissPair, suggestPairs, type Pair } from "@/lib/catalogClient";
import type { CatalogMessages } from "@/lib/i18n/catalog";

type State =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "ready"; pairs: Pair[] }
  | { status: "error"; message: string };

/**
 * "Suggest pairs" (spec 043 US5): the model's likely English and Spanish pairs of this catalog.
 * Accept opens the merge confirmation prefilled; Dismiss is remembered for the notebook. A
 * suggestion changes nothing by itself (FR-009c).
 */
export function PairSuggestions({
  t,
  notebookId,
  onAccept,
  onAnnounce,
}: {
  t: CatalogMessages;
  notebookId: string;
  onAccept: (pair: Pair) => void;
  onAnnounce: (message: string) => void;
}) {
  const [state, setState] = useState<State>({ status: "idle" });

  async function ask() {
    setState({ status: "loading" });
    const result = await suggestPairs(notebookId);
    if (result.ok) setState({ status: "ready", pairs: result.value });
    else
      setState({
        status: "error",
        message: result.status === 429 ? t.pairsLimit : t.pairsError,
      });
  }

  async function dismiss(pair: Pair) {
    if (state.status !== "ready") return;
    const before = state.pairs;
    setState({ status: "ready", pairs: before.filter((p) => p !== pair) });
    const result = await dismissPair(notebookId, pair);
    if (result.ok) onAnnounce(t.dismissed);
    else {
      setState({ status: "ready", pairs: before });
      onAnnounce(t.saveError);
    }
  }

  return (
    <section className="flex min-w-0 flex-col gap-2" aria-label={t.suggest}>
      <GhostButton
        type="button"
        className="self-start"
        loading={state.status === "loading"}
        disabled={state.status === "loading"}
        onClick={() => void ask()}
      >
        {t.suggest}
      </GhostButton>
      {state.status === "loading" ? <CauldronLoader label={t.suggesting} /> : null}
      {state.status === "error" ? (
        <p className="m-0 text-[0.9rem] text-muted" role="alert">
          {state.message}
        </p>
      ) : null}
      {state.status === "ready" ? (
        state.pairs.length === 0 ? (
          <p className="m-0 text-[0.9rem] text-muted">{t.noPairs}</p>
        ) : (
          <>
            <p className="m-0 text-[0.95rem] text-foreground">{t.pairsIntro}</p>
            <ul className="m-0 flex list-none flex-col gap-1 p-0">
              {state.pairs.map((pair) => (
                <li
                  key={`${pair.en}|${pair.es}`}
                  className="flex min-w-0 items-center justify-between gap-2 rounded-[var(--radius-md)] border border-border bg-surface py-1 pr-1 pl-3"
                >
                  <span className="min-w-0 truncate text-[0.95rem] text-foreground">
                    {pair.en} · {pair.es}
                  </span>
                  <span className="flex shrink-0 gap-1">
                    <IconButton
                      variant="ghost"
                      className="size-9"
                      label={t.accept(pair.en, pair.es)}
                      icon={<CheckIcon className="size-5" />}
                      onClick={() => onAccept(pair)}
                    />
                    <IconButton
                      variant="ghost"
                      className="size-9"
                      label={t.dismiss(pair.en, pair.es)}
                      icon={<CloseIcon className="size-5" />}
                      onClick={() => void dismiss(pair)}
                    />
                  </span>
                </li>
              ))}
            </ul>
          </>
        )
      ) : null}
    </section>
  );
}
