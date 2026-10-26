/**
 * Text for recipe capture: the add-recipe options, the text sheet, the draft review page
 * and the messages per API `code` (spec 016, contracts/capture-ui.md).
 *
 * English only in this feature. Internationalization (English and Spanish, chosen by the
 * account language) is a later story, after MVP (FR-034). Keep every string here.
 */

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
  oneRecipe: "Upload only one recipe at a time",
  unavailable: "The assistant isn't responding. Your text is kept — try again.",
  limit: "We've hit the assistant's limit. Try again in a minute.",
  invalidOutput: "We couldn't read that recipe. Try rephrasing or adding detail.",
  misconfigured: "Assistant misconfigured. Your text is kept",
  archived: "This kitchen is archived, so recipes can't be added.",
  notFound: "This kitchen is unavailable.",
  newNotebook: "a new notebook, created when the recipe is saved",
  reviewTitle: "Review recipe",
  forNotebook: (name: string) => `For: ${name}`,
  titleLabel: "Title",
  servingsLabel: "Base servings",
  estimated: "estimated",
  mainIngredients: "Main ingredients",
  cuisines: "Cuisines",
  variant: (tag: string) => `Variant · ${tag}`,
  addMainIngredient: "Add main ingredient",
  addCuisine: "Add cuisine",
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
  moveUp: "Move up",
  moveDown: "Move down",
  steps: "Steps",
  addStep: "Add step",
  stepLabel: (number: number) => `Step ${number}`,
  close: "Close",
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
    sizeOnlyForUnit: "Size is only for counted items.",
    sizeInvalid: "Choose small, medium or large.",
    stepsRequired: "Add at least one step.",
    mainIngredientsMax: "Choose at most two main ingredients.",
    cuisinesMax: "Choose at most two cuisines.",
  },
} as const;

/** The message shown for an API `code` (contracts/capture-api.md). */
export function messageForCode(code: string, reason?: string, max?: number): string {
  switch (code) {
    case "not_a_recipe":
      return reason ? `${captureMessages.notARecipe} ${reason}` : captureMessages.notARecipe;
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
    case "notebook_not_found":
    case "kitchen_not_found":
      return captureMessages.notFound;
    default:
      return captureMessages.unavailable;
  }
}
