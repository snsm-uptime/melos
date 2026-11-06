/** Catalog management on the Ingredients page, EN/ES (spec 043). No codes shown to the member. */

export const catalogMessages = {
  en: {
    notebookLabel: "Notebook",
    allNotebooks: "All notebooks (where to buy)",
    searchNotebooks: "Search notebooks",
    noNotebookMatch: "No notebook matches.",
    loading: "Loading the catalog",
    loadError: "Could not load this catalog. Try again.",
    retry: "Try again",
    readOnly: "You can read this catalog but not change it.",
    empty: "This notebook has no ingredients yet.",
    columns: {
      name: "Ingredient",
      language: "Language",
      otherNames: "Other names",
      recipes: "Recipes",
      actions: "Actions",
    },
    languages: { en: "English", es: "Spanish" },
    languageShort: { en: "EN", es: "ES" },
    noLanguage: "Not set",
    spelling: "spelling",
    rename: (name: string) => `Rename ${name}`,
    merge: (name: string) => `Merge ${name}`,
    remove: (name: string) => `Delete ${name}`,
    split: (name: string) => `Split ${name} out`,
    cancel: "Cancel",
    close: "Close",
    reload: "Someone changed this name first. The catalog was reloaded.",
    saveError: "Could not save that. Try again.",
    // Merge
    mergeTitle: (name: string) => `Merge ${name}`,
    keepLabel: "Name to keep",
    keepPlaceholder: "Pick the name to keep",
    searchNames: "Search names",
    noNameMatch: "No name matches.",
    swap: "Keep the other name",
    languageOf: (name: string) => `Language of ${name}`,
    previewLoading: "Finding the notebooks",
    previewIntro: (merged: string, kept: string) =>
      `“${merged}” becomes another name of “${kept}”. These notebooks change:`,
    previewRow: (name: string, count: number) =>
      count === 1 ? `${name}: 1 recipe uses it` : `${name}: ${count} recipes use it`,
    noNotebooks: "No notebook you can change has both names.",
    sameIngredient: "These two names are already one ingredient.",
    unknownName: "One of these names is no longer in the catalog.",
    confirmMerge: "Merge",
    merged: (merged: string, kept: string, count: number) =>
      count === 1
        ? `Merged “${merged}” into “${kept}” in 1 notebook.`
        : `Merged “${merged}” into “${kept}” in ${count} notebooks.`,
    skipped: (count: number) =>
      count === 1
        ? "1 notebook was skipped because it changed. Try again there."
        : `${count} notebooks were skipped because they changed. Try again there.`,
    // Rename
    renameTitle: (name: string) => `Rename ${name}`,
    newName: "New name",
    nameLanguage: "Language of the name",
    save: "Save",
    nameBlank: "A name can't be empty.",
    nameExists: (existing: string) => `“${existing}” is already in this catalog.`,
    mergeInto: (existing: string) => `Merge into ${existing}`,
    ownOtherName: (name: string, kept: string) =>
      `“${name}” is already another name of “${kept}”. Split it out first to rename to it.`,
    renamed: (name: string) => `Renamed to “${name}”.`,
    languageSaved: (name: string) => `Saved the language of “${name}”.`,
    // Delete
    deleteTitle: (name: string) => `Delete ${name}?`,
    deleteBody: "No recipe uses it. It is removed with its other names.",
    deleteConfirm: "Delete",
    inUse: (count: number) =>
      count === 1
        ? "1 recipe uses this name, so it can't be deleted. Merge it into another name instead."
        : `${count} recipes use this name, so it can't be deleted. Merge it into another name instead.`,
    mergeInstead: "Merge instead",
    deleted: (name: string) => `Deleted “${name}”.`,
    // Split
    splitTitle: (name: string) => `Split ${name} out?`,
    splitBody: (name: string, kept: string) =>
      `“${name}” becomes its own ingredient again, apart from “${kept}”. Every recipe keeps the words it shows now.`,
    splitConfirm: "Split",
    splitDone: (name: string) => `“${name}” is its own ingredient again.`,
    // Pairs
    suggest: "Suggest pairs",
    suggesting: "Looking for pairs",
    pairsIntro: "These English and Spanish names may be the same ingredient:",
    noPairs: "No likely pairs found.",
    pairsError: "No suggestions could be made right now. You can still merge names yourself.",
    pairsLimit: "Too many requests. Try again in a few minutes.",
    accept: (en: string, es: string) => `Merge ${en} and ${es}`,
    dismiss: (en: string, es: string) => `Not the same: ${en} and ${es}`,
    dismissed: "That pair won't be suggested again.",
  },
  es: {
    notebookLabel: "Cuaderno",
    allNotebooks: "Todos los cuadernos (dónde comprar)",
    searchNotebooks: "Buscar cuadernos",
    noNotebookMatch: "Ningún cuaderno coincide.",
    loading: "Cargando el catálogo",
    loadError: "No se pudo cargar este catálogo. Inténtalo de nuevo.",
    retry: "Intentar de nuevo",
    readOnly: "Puedes leer este catálogo, pero no cambiarlo.",
    empty: "Este cuaderno aún no tiene ingredientes.",
    columns: {
      name: "Ingrediente",
      language: "Idioma",
      otherNames: "Otros nombres",
      recipes: "Recetas",
      actions: "Acciones",
    },
    languages: { en: "Inglés", es: "Español" },
    languageShort: { en: "IN", es: "ES" },
    noLanguage: "Sin indicar",
    spelling: "variante",
    rename: (name: string) => `Renombrar ${name}`,
    merge: (name: string) => `Unir ${name}`,
    remove: (name: string) => `Eliminar ${name}`,
    split: (name: string) => `Separar ${name}`,
    cancel: "Cancelar",
    close: "Cerrar",
    reload: "Alguien cambió este nombre antes. El catálogo se ha recargado.",
    saveError: "No se pudo guardar. Inténtalo de nuevo.",
    mergeTitle: (name: string) => `Unir ${name}`,
    keepLabel: "Nombre que se queda",
    keepPlaceholder: "Elige el nombre que se queda",
    searchNames: "Buscar nombres",
    noNameMatch: "Ningún nombre coincide.",
    swap: "Quedarse con el otro nombre",
    languageOf: (name: string) => `Idioma de ${name}`,
    previewLoading: "Buscando los cuadernos",
    previewIntro: (merged: string, kept: string) =>
      `«${merged}» pasa a ser otro nombre de «${kept}». Cambian estos cuadernos:`,
    previewRow: (name: string, count: number) =>
      count === 1 ? `${name}: lo usa 1 receta` : `${name}: lo usan ${count} recetas`,
    noNotebooks: "Ningún cuaderno que puedas cambiar tiene los dos nombres.",
    sameIngredient: "Estos dos nombres ya son un mismo ingrediente.",
    unknownName: "Uno de estos nombres ya no está en el catálogo.",
    confirmMerge: "Unir",
    merged: (merged: string, kept: string, count: number) =>
      count === 1
        ? `«${merged}» se unió a «${kept}» en 1 cuaderno.`
        : `«${merged}» se unió a «${kept}» en ${count} cuadernos.`,
    skipped: (count: number) =>
      count === 1
        ? "Se omitió 1 cuaderno porque cambió. Inténtalo de nuevo allí."
        : `Se omitieron ${count} cuadernos porque cambiaron. Inténtalo de nuevo allí.`,
    renameTitle: (name: string) => `Renombrar ${name}`,
    newName: "Nombre nuevo",
    nameLanguage: "Idioma del nombre",
    save: "Guardar",
    nameBlank: "El nombre no puede quedar vacío.",
    nameExists: (existing: string) => `«${existing}» ya está en este catálogo.`,
    mergeInto: (existing: string) => `Unir a ${existing}`,
    ownOtherName: (name: string, kept: string) =>
      `«${name}» ya es otro nombre de «${kept}». Sepáralo primero para renombrar a ese nombre.`,
    renamed: (name: string) => `Renombrado a «${name}».`,
    languageSaved: (name: string) => `Se guardó el idioma de «${name}».`,
    deleteTitle: (name: string) => `¿Eliminar ${name}?`,
    deleteBody: "Ninguna receta lo usa. Se elimina con sus otros nombres.",
    deleteConfirm: "Eliminar",
    inUse: (count: number) =>
      count === 1
        ? "1 receta usa este nombre, así que no se puede eliminar. Únelo a otro nombre."
        : `${count} recetas usan este nombre, así que no se puede eliminar. Únelo a otro nombre.`,
    mergeInstead: "Unir en su lugar",
    deleted: (name: string) => `Se eliminó «${name}».`,
    splitTitle: (name: string) => `¿Separar ${name}?`,
    splitBody: (name: string, kept: string) =>
      `«${name}» vuelve a ser un ingrediente propio, aparte de «${kept}». Cada receta sigue mostrando las mismas palabras.`,
    splitConfirm: "Separar",
    splitDone: (name: string) => `«${name}» vuelve a ser un ingrediente propio.`,
    suggest: "Sugerir parejas",
    suggesting: "Buscando parejas",
    pairsIntro: "Estos nombres en inglés y en español pueden ser el mismo ingrediente:",
    noPairs: "No se encontraron parejas probables.",
    pairsError: "Ahora no se pueden hacer sugerencias. Puedes unir nombres tú mismo.",
    pairsLimit: "Demasiadas solicitudes. Inténtalo en unos minutos.",
    accept: (en: string, es: string) => `Unir ${en} y ${es}`,
    dismiss: (en: string, es: string) => `No son lo mismo: ${en} y ${es}`,
    dismissed: "Esa pareja no se volverá a sugerir.",
  },
} as const;

export type CatalogMessages = (typeof catalogMessages)[keyof typeof catalogMessages];
