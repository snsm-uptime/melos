/** Shared table text, EN/ES (spec 066 contracts/data-table.md). Spanish awaits the owner's review. */

import type { DataTableLabels } from "@/components/DataTable/types";

import type { Locale } from "./locale";

export const tableMessages: Record<Locale, DataTableLabels> = {
  en: {
    searchLabel: "Search this table",
    searchPlaceholder: "Search",
    noMatches: "Nothing matches your search.",
    matchCount: (n) => (n === 1 ? "1 row shown" : `${n} rows shown`),
    sortBy: (label) => `Sort by ${label}`,
    sortLevel: (label, level, direction) =>
      `${label}, sort level ${level}, ${direction === "asc" ? "ascending" : "descending"}`,
    clearSort: "Clear sort",
  },
  es: {
    searchLabel: "Buscar en esta tabla",
    searchPlaceholder: "Buscar",
    noMatches: "Nada coincide con tu búsqueda.",
    matchCount: (n) => (n === 1 ? "1 fila mostrada" : `${n} filas mostradas`),
    sortBy: (label) => `Ordenar por ${label}`,
    sortLevel: (label, level, direction) =>
      `${label}, nivel de orden ${level}, ${direction === "asc" ? "ascendente" : "descendente"}`,
    clearSort: "Quitar orden",
  },
};
