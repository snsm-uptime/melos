/** Shopping list export text, EN/ES (spec 024). No codes shown to the member. */

export const shoppingExportMessages = {
  en: {
    title: "Export this list",
    copyBox: "Shopping list as Markdown",
    copy: "Copy",
    copied: "Copied. Paste it wherever you need the list.",
    downloadPdf: "Download PDF",
    loading: "Loading the export",
    loadError: "Could not load the export. Try again.",
    retry: "Try again",
    pdfError: "The PDF could not be made. The copy above still works.",
    emptyHint: "Add recipes or items to the list first.",
  },
  es: {
    title: "Exportar esta lista",
    copyBox: "Lista de compras en Markdown",
    copy: "Copiar",
    copied: "Copiado. Pégala donde la necesites.",
    downloadPdf: "Descargar PDF",
    loading: "Cargando la exportación",
    loadError: "No se pudo cargar la exportación. Inténtalo de nuevo.",
    retry: "Intentar de nuevo",
    pdfError: "No se pudo crear el PDF. La copia de arriba sigue funcionando.",
    emptyHint: "Primero añade recetas o artículos a la lista.",
  },
} as const;
