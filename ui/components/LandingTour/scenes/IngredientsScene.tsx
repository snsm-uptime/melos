"use client";

import { ActionDialog } from "@/components/ActionDialog";
import { catalogTable } from "@/components/CatalogManager";
import { DataTable } from "@/components/DataTable";
import { SearchableSelect } from "@/components/SearchableSelect";
import { catalogMessages } from "@/lib/i18n/catalog";
import { landingMessages } from "@/lib/i18n/landing";
import type { Locale } from "@/lib/i18n/locale";
import { tableMessages } from "@/lib/i18n/table";

import { catalogRows } from "./data";
import { ignore, inAt, Scene, Swap } from "./parts";

/**
 * Ingredients (FR-006.5): the catalog table with "onions" and "onion", the merge dialog keeping
 * "onion", then the table with one row: "onion", with "onions" as a spelling and its name in the
 * other language. The table is the Ingredients page's, with its own schema; the dialog is the
 * app's, drawn in place, with the fields MergeDialog shows once its preview has loaded
 * (MergeDialog reads that preview from the api, which a scene never calls).
 */
export function IngredientsScene({ locale }: { locale: Locale }) {
  const t = landingMessages[locale].demo.ingredients;
  const c = catalogMessages[locale];
  const rows = catalogRows(locale);
  const table = (ingredients: typeof rows.before) => (
    <DataTable
      schema={catalogTable(c, true, ignore)}
      rows={ingredients}
      locale={locale}
      labels={tableMessages[locale]}
      empty={c.empty}
    />
  );
  return (
    <Scene>
      <Swap
        slot={2}
        before={<div className={inAt(1)}>{table(rows.before)}</div>}
        after={
          <Swap
            slot={4}
            before={
              <ActionDialog
                open
                title={c.mergeTitle(t.merged)}
                confirmLabel={c.confirmMerge}
                cancelLabel={c.cancel}
                onOpenChange={ignore}
                onConfirm={ignore}
              >
                <div className="flex flex-col gap-4">
                  <div className="flex flex-col gap-1">
                    <span className="text-[0.9rem] text-muted">{c.keepLabel}</span>
                    <SearchableSelect
                      aria-label={c.keepLabel}
                      placeholder={c.keepPlaceholder}
                      value={t.kept}
                      options={[{ value: t.kept, label: t.kept }]}
                      searchLabel={c.searchNames}
                      noResults={c.noNameMatch}
                      onChange={ignore}
                      className="min-h-11 rounded-[var(--radius-md)] border border-border bg-background px-3 text-left text-[0.95rem] text-foreground"
                    />
                  </div>
                  <div className="flex flex-col gap-1">
                    <p className="m-0 text-[0.95rem] text-foreground">{c.previewIntro(t.merged, t.kept)}</p>
                    <ul className="m-0 list-disc pl-5 text-[0.95rem] text-foreground">
                      <li>{c.previewRow(t.notebook, 1)}</li>
                    </ul>
                  </div>
                </div>
              </ActionDialog>
            }
            after={
              <div className="flex flex-col gap-4">
                <p className={`m-0 text-[0.9rem] text-foreground ${inAt(5)}`}>
                  {c.merged(t.merged, t.kept, 1)}
                </p>
                {table(rows.after)}
              </div>
            }
          />
        }
      />
    </Scene>
  );
}
