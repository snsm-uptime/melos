/**
 * Text for recipe capture: the add-recipe options, the text sheet, the draft review page
 * and the messages per API `code` (spec 016, contracts/capture-ui.md).
 *
 * English only in this feature. Internationalization (English and Spanish, chosen by the
 * account language) is a later story, after MVP (FR-034). Keep every string here.
 */

import type { CaptureMessage } from "@/lib/capture/captureStore";

export const captureMessages = {
  addRecipe: "Add a recipe",
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
} as const;

const MAX_LINE_SENTENCES = 5;

/** One sentence per line problem, or null for a kind the app does not show. */
function lineSentence(problem: { name: string | null; kind: string }): string | null {
  const name = problem.name ?? "this ingredient";
  switch (problem.kind) {
    case "quantity_missing":
      return `Add a quantity to ${name}.`;
    case "unit_missing":
      return `Add a unit to ${name}, such as grams, cups or units.`;
    case "unit_not_recognized":
      return `${name} uses a unit the app does not know. Use a common unit, such as grams, cups or spoons.`;
    default:
      return null;
  }
}

/** The missing-part sentences first (title, then steps), then the line sentences in order. */
function draftSentences(message: CaptureMessage): string {
  const missing = message.missing ?? [];
  const sentences: string[] = [];
  if (missing.includes("title")) sentences.push("Add a title for the recipe.");
  if (missing.includes("steps")) sentences.push("Add the steps of the recipe.");

  const lines = (message.lineProblems ?? []).flatMap((problem) => {
    const sentence = lineSentence(problem);
    return sentence ? [sentence] : [];
  });
  sentences.push(...lines.slice(0, MAX_LINE_SENTENCES));
  if (lines.length > MAX_LINE_SENTENCES) sentences.push("and more ingredients need a change.");

  return sentences.length > 0 ? sentences.join(" ") : captureMessages.unavailable;
}

/** The sentence for a not_a_recipe reason, with the ingredient when the reason is about one. */
function notARecipeSentence(message: CaptureMessage): string {
  const ingredient = message.ingredient;
  switch (message.reason) {
    case "question_or_request":
      if (ingredient === undefined) {
        return "That doesn't look like a recipe. It reads as a question or request. Clarify the text: paste the full recipe, with its ingredients and steps.";
      }
      return `That reads as a question about ${ingredient ?? "this ingredient"}, not a recipe. Clarify the text: paste the full recipe, with the amount and unit of ${ingredient ?? "this ingredient"} and its steps.`;
    case "not_food":
      return "That doesn't look like a recipe. It is not about food. Paste the full recipe, with its ingredients and steps.";
    case "story_or_article":
      return "That doesn't look like a recipe. It reads as a story or article. Paste only the recipe, with its ingredients and steps.";
    default:
      return captureMessages.notARecipe;
  }
}

/** The message shown for an API refusal (contracts/capture-messages.md). */
export function messageForCode(message: CaptureMessage, max?: number): string {
  switch (message.code) {
    case "draft_incomplete":
    case "ingredient_line_problem":
      return draftSentences(message);
    case "not_a_recipe":
      return notARecipeSentence(message);
    case "one_recipe_at_a_time":
      return captureMessages.oneRecipe;
    case "ai_limit_reached":
      return captureMessages.limit;
    case "ai_invalid_output":
      return captureMessages.invalidOutput;
    case "ai_misconfigured":
      return captureMessages.misconfigured;
    case "text_too_long":
      return captureMessages.tooLong(max ?? 5000);
    case "kitchen_archived":
      return captureMessages.archived;
    case "notebook_gone":
      return captureMessages.notebookGone;
    case "invalid_recipe":
      return captureMessages.invalidRecipe;
    case "save_unavailable":
      return captureMessages.saveUnavailable;
    case "notebook_not_found":
    case "kitchen_not_found":
      return captureMessages.notFound;
    default:
      return captureMessages.unavailable;
  }
}
