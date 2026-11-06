/**
 * Text for sharing a recipe with a person from the recipe page, EN/ES (spec 071, FR-012).
 * No codes or technical terms are shown to the member.
 */

const en = {
  shareButton: "Share recipe",
  shareTitle: "Share this recipe",
  shareClose: "Close",
  shareSearchLabel: "Find a person",
  sharePlaceholder: "Choose a person",
  shareSend: "Send recipe",
  shareNoResults: "No one matches that name.",
  shareNoCandidates:
    "Share a kitchen or a recipe book with someone to send them recipes.",
  shareLoading: "Loading people…",
  shareSent: (alias: string) => `Recipe sent to ${alias}. It is in their recipe book.`,
  shareErrorRecipeNotFound: "That recipe isn't available.",
  shareErrorRecipientNotFound: "That person can't be found.",
  shareErrorSelf: "You can't share a recipe with yourself.",
  shareErrorNoDefault: "That person's recipe book isn't ready yet. Try again later.",
  shareErrorGeneric: "The recipe could not be sent. Try again.",
};

const es: Partial<typeof en> = {
  shareButton: "Compartir receta",
  shareTitle: "Compartir esta receta",
  shareClose: "Cerrar",
  shareSearchLabel: "Buscar una persona",
  sharePlaceholder: "Elige una persona",
  shareSend: "Enviar receta",
  shareNoResults: "Nadie coincide con ese nombre.",
  shareNoCandidates:
    "Comparte una cocina o un libro de recetas con alguien para enviarle recetas.",
  shareLoading: "Cargando personas…",
  shareSent: (alias: string) => `Receta enviada a ${alias}. Está en su libro de recetas.`,
  shareErrorRecipeNotFound: "Esa receta no está disponible.",
  shareErrorRecipientNotFound: "No se encuentra a esa persona.",
  shareErrorSelf: "No puedes compartir una receta contigo mismo.",
  shareErrorNoDefault: "El libro de recetas de esa persona aún no está listo. Inténtalo más tarde.",
  shareErrorGeneric: "No se pudo enviar la receta. Inténtalo de nuevo.",
};

export const recipeShareMessages = { en, es } as const;
