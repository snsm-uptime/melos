/**
 * Text for recipe capture: the add-recipe options, the text sheet, the draft review page
 * and the messages per API `code` (spec 016, contracts/capture-ui.md), in English and Spanish
 * (spec 063). Keep every string here; read them through `useCaptureMessages()` in a component.
 */

import type { CaptureMessage } from "@/lib/capture/captureStore";

import type { Locale } from "./locale";
import { messagesFor } from "./messages";

const en = {
  addRecipe: "Add a recipe",
  addRecipeButton: "Add recipe",
  optionUrl: "URL",
  optionUrlNote: "Not available yet",
  optionPicture: "Picture",
  optionPictureNote: "Coming soon",
  optionText: "Text",
  notebookPicker: "Notebook",
  recipeText: "Recipe text",
  counterNear: (count: number, max: number) => `${count} of ${max} characters`,
  submit: "Read recipe",
  submitting: "Reading your recipe…",
  tooLong: (max: number) => `That text is too long. Paste up to ${max} characters.`,
  notARecipe: "That doesn't look like a recipe.",
  oneRecipe: "Only one recipe can be added at a time. Paste them one by one.",
  unavailable: "The assistant isn't responding. Your text is kept — try again.",
  limit: "We've hit the assistant's limit. Try again in a minute.",
  invalidOutput:
    "The app could not build a recipe from this text. Try again, or shorten the text to one recipe.",
  misconfigured: "Assistant misconfigured. Your text is kept",
  archived: "This kitchen is archived, so recipes can't be added.",
  notFound: "This kitchen is unavailable.",
  notebookGone: "This notebook no longer exists, or you no longer have access to it.",
  invalidRecipe: "The recipe breaks a rule. Check the ingredient lines and try again.",
  saveUnavailable: "We couldn't save the recipe. Your changes are kept. Try again.",
  newNotebook: "a new notebook, created when the recipe is saved",
  reviewTitle: "Review recipe",
  forNotebook: (name: string) => `For: ${name}`,
  titleLabel: "Title",
  servingsLabel: "Base servings",
  estimated: "estimated",
  // MVP-OUT: mainIngredients: "Main ingredients",
  // MVP-OUT: cuisines: "Cuisines",
  // MVP-OUT: variant: (tag: string) => `Variant · ${tag}`,
  // MVP-OUT: addMainIngredient: "Add main ingredient",
  // MVP-OUT: addCuisine: "Add cuisine",
  remove: "Remove",
  ingredients: "Ingredients",
  ingredientName: "Name",
  quantity: "Quantity",
  unit: "Unit",
  size: "Size",
  preparation: "Preparation",
  note: "Note",
  vague: "Vague amount",
  addIngredient: "Add ingredient",
  newIngredient: "new ingredient",
  matchControl: "Catalog match",
  changeItem: (from: string, to: string) => `${from} → ${to}`,
  undoChange: "Undo",
  moveUp: "Move up",
  moveDown: "Move down",
  steps: "Steps",
  addStep: "Add step",
  stepLabel: (number: number) => `Step ${number}`,
  close: "Close",
  save: "Save recipe",
  saving: "Saving…",
  saved: "Recipe saved",
  discard: "Discard",
  back: "Back",
  leaveTitle: "Leave without saving?",
  leaveBody: "Your changes to this draft will be lost.",
  stay: "Stay",
  leave: "Leave",
  missingTitle: "Add a title for the recipe.",
  missingSteps: "Add the steps of the recipe.",
  thisIngredient: "this ingredient",
  lineQuantity: (name: string) => `Add a quantity to ${name}.`,
  lineUnit: (name: string) => `Add a unit to ${name}, such as grams, cups or units.`,
  lineUnitUnknown: (name: string) =>
    `${name} uses a unit the app does not know. Use a common unit, such as grams, cups or spoons.`,
  moreLines: "and more ingredients need a change.",
  notARecipeQuestion:
    "That doesn't look like a recipe. It reads as a question or request. Clarify the text: paste the full recipe, with its ingredients and steps.",
  notARecipeQuestionAbout: (ingredient: string) =>
    `That reads as a question about ${ingredient}, not a recipe. Clarify the text: paste the full recipe, with the amount and unit of ${ingredient} and its steps.`,
  notARecipeNotFood:
    "That doesn't look like a recipe. It is not about food. Paste the full recipe, with its ingredients and steps.",
  notARecipeStory:
    "That doesn't look like a recipe. It reads as a story or article. Paste only the recipe, with its ingredients and steps.",
  errors: {
    titleRequired: "Add a title.",
    titleTooLong: "Keep the title under 200 characters.",
    servingsInvalid: "Servings must be a whole number of at least 1.",
    amountAndUnit: "Add an amount and a unit, or mark it as vague.",
    vagueHasAmount: "A vague amount has no number or unit.",
    vagueNeedsNote: "Write the amount in words, for example \"to taste\".",
    sizeOnlyForUnit: "Size is only for counted items.",
    sizeInvalid: "Choose small, medium or large.",
    stepsRequired: "Add at least one step.",
    // MVP-OUT: mainIngredientsMax: "Choose at most two main ingredients.",
    // MVP-OUT: cuisinesMax: "Choose at most two cuisines.",
  },
};

type CaptureMessages = typeof en;

const es: CaptureMessages = {
  addRecipe: "Agregar una receta",
  addRecipeButton: "Agregar receta",
  optionUrl: "URL",
  optionUrlNote: "Aún no disponible",
  optionPicture: "Imagen",
  optionPictureNote: "Próximamente",
  optionText: "Texto",
  notebookPicker: "Cuaderno",
  recipeText: "Texto de la receta",
  counterNear: (count: number, max: number) => `${count} de ${max} caracteres`,
  submit: "Leer receta",
  submitting: "Leyendo tu receta…",
  tooLong: (max: number) => `Ese texto es demasiado largo. Pega hasta ${max} caracteres.`,
  notARecipe: "Eso no parece una receta.",
  oneRecipe: "Solo se puede agregar una receta a la vez. Pégalas una por una.",
  unavailable: "El asistente no responde. Tu texto se conserva: inténtalo de nuevo.",
  limit: "Llegamos al límite del asistente. Inténtalo de nuevo en un minuto.",
  invalidOutput:
    "La app no pudo armar una receta con este texto. Inténtalo de nuevo o acórtalo a una sola receta.",
  misconfigured: "El asistente está mal configurado. Tu texto se conserva.",
  archived: "Esta cocina está archivada, así que no se pueden agregar recetas.",
  notFound: "Esta cocina no está disponible.",
  notebookGone: "Este cuaderno ya no existe, o ya no tienes acceso a él.",
  invalidRecipe: "La receta incumple una regla. Revisa los ingredientes e inténtalo de nuevo.",
  saveUnavailable: "No pudimos guardar la receta. Tus cambios se conservan. Inténtalo de nuevo.",
  newNotebook: "un cuaderno nuevo, que se crea al guardar la receta",
  reviewTitle: "Revisar receta",
  forNotebook: (name: string) => `Para: ${name}`,
  titleLabel: "Título",
  servingsLabel: "Porciones base",
  estimated: "estimadas",
  remove: "Quitar",
  ingredients: "Ingredientes",
  ingredientName: "Nombre",
  quantity: "Cantidad",
  unit: "Unidad",
  size: "Tamaño",
  preparation: "Preparación",
  note: "Nota",
  vague: "Cantidad imprecisa",
  addIngredient: "Agregar ingrediente",
  newIngredient: "ingrediente nuevo",
  matchControl: "Coincidencia del catálogo",
  changeItem: (from: string, to: string) => `${from} → ${to}`,
  undoChange: "Deshacer",
  moveUp: "Subir",
  moveDown: "Bajar",
  steps: "Pasos",
  addStep: "Agregar paso",
  stepLabel: (number: number) => `Paso ${number}`,
  close: "Cerrar",
  save: "Guardar receta",
  saving: "Guardando…",
  saved: "Receta guardada",
  discard: "Descartar",
  back: "Volver",
  leaveTitle: "¿Salir sin guardar?",
  leaveBody: "Perderás los cambios de este borrador.",
  stay: "Quedarme",
  leave: "Salir",
  missingTitle: "Agrega un título para la receta.",
  missingSteps: "Agrega los pasos de la receta.",
  thisIngredient: "este ingrediente",
  lineQuantity: (name: string) => `Agrega una cantidad a ${name}.`,
  lineUnit: (name: string) => `Agrega una unidad a ${name}, como gramos, tazas o unidades.`,
  lineUnitUnknown: (name: string) =>
    `${name} usa una unidad que la app no conoce. Usa una unidad común, como gramos, tazas o cucharas.`,
  moreLines: "y otros ingredientes necesitan un cambio.",
  notARecipeQuestion:
    "Eso no parece una receta. Se lee como una pregunta o una petición. Aclara el texto: pega la receta completa, con sus ingredientes y pasos.",
  notARecipeQuestionAbout: (ingredient: string) =>
    `Eso se lee como una pregunta sobre ${ingredient}, no como una receta. Aclara el texto: pega la receta completa, con la cantidad y la unidad de ${ingredient} y sus pasos.`,
  notARecipeNotFood:
    "Eso no parece una receta. No trata de comida. Pega la receta completa, con sus ingredientes y pasos.",
  notARecipeStory:
    "Eso no parece una receta. Se lee como un cuento o un artículo. Pega solo la receta, con sus ingredientes y pasos.",
  errors: {
    titleRequired: "Agrega un título.",
    titleTooLong: "Mantén el título por debajo de 200 caracteres.",
    servingsInvalid: "Las porciones deben ser un número entero de al menos 1.",
    amountAndUnit: "Agrega una cantidad y una unidad, o márcala como imprecisa.",
    vagueHasAmount: "Una cantidad imprecisa no lleva número ni unidad.",
    vagueNeedsNote: "Escribe la cantidad con palabras, por ejemplo \"al gusto\".",
    sizeOnlyForUnit: "El tamaño es solo para artículos que se cuentan.",
    sizeInvalid: "Elige pequeño, mediano o grande.",
    stepsRequired: "Agrega al menos un paso.",
  },
};

/** Every capture message in both languages; a key missing in Spanish is a type error. */
export const captureText = { en, es } as const;

/** The capture messages for a language, with English under any message missing in Spanish. */
export function captureMessagesFor(locale: Locale): CaptureMessages {
  return messagesFor(captureText, locale);
}

const MAX_LINE_SENTENCES = 5;

/** One sentence per line problem, or null for a kind the app does not show. */
function lineSentence(
  t: CaptureMessages,
  problem: { name: string | null; kind: string },
): string | null {
  const name = problem.name ?? t.thisIngredient;
  switch (problem.kind) {
    case "quantity_missing":
      return t.lineQuantity(name);
    case "unit_missing":
      return t.lineUnit(name);
    case "unit_not_recognized":
      return t.lineUnitUnknown(name);
    default:
      return null;
  }
}

/** The missing-part sentences first (title, then steps), then the line sentences in order. */
function draftSentences(t: CaptureMessages, message: CaptureMessage): string {
  const missing = message.missing ?? [];
  const sentences: string[] = [];
  if (missing.includes("title")) sentences.push(t.missingTitle);
  if (missing.includes("steps")) sentences.push(t.missingSteps);

  const lines = (message.lineProblems ?? []).flatMap((problem) => {
    const sentence = lineSentence(t, problem);
    return sentence ? [sentence] : [];
  });
  sentences.push(...lines.slice(0, MAX_LINE_SENTENCES));
  if (lines.length > MAX_LINE_SENTENCES) sentences.push(t.moreLines);

  return sentences.length > 0 ? sentences.join(" ") : t.unavailable;
}

/** The sentence for a not_a_recipe reason, with the ingredient when the reason is about one. */
function notARecipeSentence(t: CaptureMessages, message: CaptureMessage): string {
  const ingredient = message.ingredient;
  switch (message.reason) {
    case "question_or_request":
      if (ingredient === undefined) return t.notARecipeQuestion;
      return t.notARecipeQuestionAbout(ingredient ?? t.thisIngredient);
    case "not_food":
      return t.notARecipeNotFood;
    case "story_or_article":
      return t.notARecipeStory;
    default:
      return t.notARecipe;
  }
}

/** The message shown for an API refusal (contracts/capture-messages.md), in the screen's language. */
export function messageForCode(message: CaptureMessage, locale: Locale, max?: number): string {
  const t = captureMessagesFor(locale);
  switch (message.code) {
    case "draft_incomplete":
    case "ingredient_line_problem":
      return draftSentences(t, message);
    case "not_a_recipe":
      return notARecipeSentence(t, message);
    case "one_recipe_at_a_time":
      return t.oneRecipe;
    case "ai_limit_reached":
      return t.limit;
    case "ai_invalid_output":
      return t.invalidOutput;
    case "ai_misconfigured":
      return t.misconfigured;
    case "text_too_long":
      return t.tooLong(max ?? 5000);
    case "kitchen_archived":
      return t.archived;
    case "notebook_gone":
      return t.notebookGone;
    case "invalid_recipe":
      return t.invalidRecipe;
    case "save_unavailable":
      return t.saveUnavailable;
    case "notebook_not_found":
    case "kitchen_not_found":
      return t.notFound;
    default:
      return t.unavailable;
  }
}
