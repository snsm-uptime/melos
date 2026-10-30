/** Shopping list text, EN/ES (spec 023, contracts/shopping-list-ui.md). No codes shown to the member. */

export const shoppingListMessages = {
  en: {
    title: "Shopping list",
    yourCall: "Your call",
    loading: "Loading the shopping list",
    loadError: "Could not load the shopping list. Try again.",
    retry: "Try again",
    noIngredients: "These recipes have no ingredients",
    recipesLabel: "Recipes",
    recipeCount: (n: number) => (n === 1 ? "1 recipe" : `${n} recipes`),
  },
  es: {
    title: "Lista de compras",
    yourCall: "A tu criterio",
    loading: "Cargando la lista de compras",
    loadError: "No se pudo cargar la lista de compras. Inténtalo de nuevo.",
    retry: "Reintentar",
    noIngredients: "Estas recetas no tienen ingredientes",
    recipesLabel: "Recetas",
    recipeCount: (n: number) => (n === 1 ? "1 receta" : `${n} recetas`),
  },
} as const;
