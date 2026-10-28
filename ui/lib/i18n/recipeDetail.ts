/**
 * Text for the recipe detail, edit and delete screens, EN/ES (spec 027). No codes or technical
 * terms are shown to the member (FR-019). The wording of a rule that breaks on save follows
 * `lib/i18n/capture.ts`.
 */

const en = {
  back: "Back",
  loading: "Loading recipe",
  estimated: "estimated",
  servings: (count: number) => (count === 1 ? "1 serving" : `${count} servings`),
  authorLabel: "Added by",
  authorUnknown: "unknown",
  notebookLabel: "Notebook",
  ingredientsTitle: "Ingredients",
  stepsTitle: "Steps",
  sourceLink: "Source",
  edit: "Edit",
  delete: "Delete",
  notAvailable: "That recipe isn't available.",
  goToNotebooks: "Go to your notebooks",
  readOnly: "You can only read this recipe.",
  loadError: "Could not load the recipe. Try again.",
  retry: "Try again",

  deleteTitle: (title: string) => `Delete “${title}”?`,
  deleteBody: "This can't be undone.",
  deleteConfirm: "Delete",
  deleting: "Deleting…",
  cancel: "Cancel",
  deleteFailed: "The recipe wasn't deleted. Try again.",

  editTitle: "Edit recipe",
  titleLabel: "Title",
  servingsLabel: "Base servings",
  save: "Save",
  saving: "Saving…",
  changed: "This recipe was changed after you opened it. Reload to see the latest version.",
  reload: "Reload",
  gone: "That recipe is no longer available.",
  saveFailed: "We couldn't save the recipe. Your changes are kept. Try again.",
  invalidRecipe: "The recipe breaks a rule. Check the ingredient lines and try again.",
  leaveTitle: "Leave without saving?",
  leaveBody: "Your changes to this recipe will be lost.",
  stay: "Stay",
  leave: "Leave",
  missingTitle: "Add a title for the recipe.",
  missingSteps: "Add the steps of the recipe.",
  missingIngredients: "Add at least one ingredient.",
  lineQuantity: (name: string) => `Add a quantity to ${name}.`,
  lineUnit: (name: string) => `Add a unit to ${name}, such as grams, cups or units.`,
  lineUnitUnknown: (name: string) =>
    `${name} uses a unit the app does not know. Use a common unit, such as grams, cups or spoons.`,
  moreLines: "and more ingredients need a change.",
  checkingNames: "Checking names…",
};

type Messages = typeof en;

const es: Messages = {
  back: "Volver",
  loading: "Cargando receta",
  estimated: "estimadas",
  servings: (count: number) => (count === 1 ? "1 porción" : `${count} porciones`),
  authorLabel: "Agregada por",
  authorUnknown: "desconocido",
  notebookLabel: "Cuaderno",
  ingredientsTitle: "Ingredientes",
  stepsTitle: "Pasos",
  sourceLink: "Fuente",
  edit: "Editar",
  delete: "Eliminar",
  notAvailable: "Esa receta no está disponible.",
  goToNotebooks: "Ir a tus cuadernos",
  readOnly: "Solo puedes leer esta receta.",
  loadError: "No se pudo cargar la receta. Inténtalo de nuevo.",
  retry: "Intentar de nuevo",

  deleteTitle: (title: string) => `¿Eliminar “${title}”?`,
  deleteBody: "Esto no se puede deshacer.",
  deleteConfirm: "Eliminar",
  deleting: "Eliminando…",
  cancel: "Cancelar",
  deleteFailed: "La receta no se eliminó. Inténtalo de nuevo.",

  editTitle: "Editar receta",
  titleLabel: "Título",
  servingsLabel: "Porciones base",
  save: "Guardar",
  saving: "Guardando…",
  changed:
    "Esta receta cambió después de que la abriste. Recarga para ver la última versión.",
  reload: "Recargar",
  gone: "Esa receta ya no está disponible.",
  saveFailed: "No pudimos guardar la receta. Tus cambios se conservan. Inténtalo de nuevo.",
  invalidRecipe: "La receta rompe una regla. Revisa los ingredientes e inténtalo de nuevo.",
  leaveTitle: "¿Salir sin guardar?",
  leaveBody: "Perderás los cambios de esta receta.",
  stay: "Quedarme",
  leave: "Salir",
  missingTitle: "Agrega un título para la receta.",
  missingSteps: "Agrega los pasos de la receta.",
  missingIngredients: "Agrega al menos un ingrediente.",
  lineQuantity: (name: string) => `Agrega una cantidad a ${name}.`,
  lineUnit: (name: string) => `Agrega una unidad a ${name}, como gramos, tazas o unidades.`,
  lineUnitUnknown: (name: string) =>
    `${name} usa una unidad que la app no conoce. Usa una unidad común, como gramos, tazas o cucharas.`,
  moreLines: "y otros ingredientes necesitan un cambio.",
  checkingNames: "Revisando nombres…",
};

export const recipeDetailMessages = { en, es } as const;

const MAX_LINE_SENTENCES = 5;

type Problem = { name: string | null; kind: string };

/** The sentences for a save that was refused: missing parts first, then lines in order. */
export function saveProblemText(
  t: Messages,
  missing: string[] | undefined,
  lineProblems: Problem[] | undefined,
): string {
  const sentences: string[] = [];
  if (missing?.includes("title")) sentences.push(t.missingTitle);
  if (missing?.includes("ingredients")) sentences.push(t.missingIngredients);
  if (missing?.includes("steps")) sentences.push(t.missingSteps);
  const lines = (lineProblems ?? []).flatMap((problem) => {
    const name = problem.name ?? "—";
    switch (problem.kind) {
      case "quantity_missing":
        return [t.lineQuantity(name)];
      case "unit_missing":
        return [t.lineUnit(name)];
      case "unit_not_recognized":
        return [t.lineUnitUnknown(name)];
      default:
        return [];
    }
  });
  sentences.push(...lines.slice(0, MAX_LINE_SENTENCES));
  if (lines.length > MAX_LINE_SENTENCES) sentences.push(t.moreLines);
  return sentences.length > 0 ? sentences.join(" ") : t.invalidRecipe;
}

export type RecipeDetailMessages = Messages;
