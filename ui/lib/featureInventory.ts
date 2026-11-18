/**
 * The feature inventory (spec 075): every feature a signed-in person can use, grouped in the
 * order a person uses the app. The signed-out landing page is built from this list, so a feature
 * added here shows on the page with no other change.
 *
 * Change rule (FR-017): a story that adds, removes or changes a feature a person can use edits
 * this module in the same change, and its backlog verification note says so. When a planned
 * feature ships, change its status to "available"; that is the only edit needed.
 * Contract: specs/075-landing-feature-tour/contracts/feature-inventory.md.
 *
 * Pure data and pure functions: no React, Next.js or client imports. Admin-only features are left
 * out, because visitors never use them.
 */

export type Localized = { en: string; es: string };
export type GroupId = "capture" | "notebooks" | "together" | "shop" | "ingredients" | "home";
export type FeatureStatus = "available" | "planned";

export type FeatureGroup = {
  id: GroupId;
  order: 1 | 2 | 3 | 4 | 5 | 6;
  title: Localized;
  lede: Localized;
};

export type Feature = {
  id: string;
  group: GroupId;
  name: Localized;
  summary: Localized;
  stories: readonly string[];
  status: FeatureStatus;
};

export const featureGroups: readonly FeatureGroup[] = [
  {
    id: "capture",
    order: 1,
    title: { en: "Capture any recipe", es: "Guarda cualquier receta" },
    lede: {
      en: "Paste a recipe, share a link or take a photo of a cookbook page. Melos turns it into a tidy recipe you check before saving.",
      es: "Pega una receta, comparte un enlace o toma una foto de un libro de cocina. Melos la convierte en una receta ordenada que revisas antes de guardar.",
    },
  },
  {
    id: "notebooks",
    order: 2,
    title: { en: "Your recipe notebooks", es: "Tus cuadernos de recetas" },
    lede: {
      en: "Keep recipes in notebooks, find them in seconds and cook for as many people as you need.",
      es: "Guarda tus recetas en cuadernos, encuéntralas en segundos y cocina para las personas que hagan falta.",
    },
  },
  {
    id: "together",
    order: 3,
    title: { en: "Cook together", es: "Cocina en compañía" },
    lede: {
      en: "Share a kitchen with the people you cook with. Everyone sees the same recipes and the same shopping list.",
      es: "Comparte una cocina con quienes cocinas. Todos ven las mismas recetas y la misma lista de compras.",
    },
  },
  {
    id: "shop",
    order: 4,
    title: { en: "Plan the week and shop", es: "Planea la semana y compra" },
    lede: {
      en: "Pick the week's recipes and get one shopping list with every amount added up for the people at your table.",
      es: "Elige las recetas de la semana y obtén una sola lista de compras con las cantidades sumadas para las personas en tu mesa.",
    },
  },
  {
    id: "ingredients",
    order: 5,
    title: { en: "Ingredients that stay tidy", es: "Ingredientes siempre en orden" },
    lede: {
      en: "One name for each ingredient, so “onions” and “onion” never end up as two lines on your list.",
      es: "Un solo nombre por ingrediente, para que «cebollas» y «cebolla» nunca sean dos líneas en tu lista.",
    },
  },
  {
    id: "home",
    order: 6,
    title: { en: "Made for your home", es: "Hecho para tu casa" },
    lede: {
      en: "Use Melos in Spanish or English, in a light or dark look, with your own name and photo.",
      es: "Usa Melos en español o en inglés, con aspecto claro u oscuro, con tu nombre y tu foto.",
    },
  },
];

export const features: readonly Feature[] = [
  // 1. Capture any recipe
  {
    id: "capture-text",
    group: "capture",
    name: { en: "Paste a recipe", es: "Pega una receta" },
    summary: {
      en: "Paste the text of any recipe and get a structured draft with its ingredients and steps.",
      es: "Pega el texto de cualquier receta y obtén un borrador con sus ingredientes y pasos.",
    },
    stories: ["S-016"],
    status: "available",
  },
  {
    id: "capture-link",
    group: "capture",
    name: { en: "Capture from a link", es: "Guarda desde un enlace" },
    summary: {
      en: "Share a recipe page's link; if a site refuses, you get a clear message saying so.",
      es: "Comparte el enlace de una página de recetas; si un sitio no lo permite, un mensaje claro te lo dice.",
    },
    stories: ["S-026", "S-078"],
    status: "available",
  },
  {
    id: "capture-photo",
    group: "capture",
    name: { en: "Capture from a photo", es: "Guarda desde una foto" },
    summary: {
      en: "Take a photo of a cookbook page and turn it into a recipe.",
      es: "Toma una foto de una página de un libro de cocina y conviértela en receta.",
    },
    stories: ["S-041"],
    status: "available",
  },
  {
    id: "capture-review",
    group: "capture",
    name: { en: "Review before saving", es: "Revisa antes de guardar" },
    summary: {
      en: "Check the draft before it is saved; clear messages name anything missing.",
      es: "Revisa el borrador antes de guardarlo; mensajes claros indican lo que falta.",
    },
    stories: ["S-016", "S-017"],
    status: "available",
  },
  {
    id: "capture-matching",
    group: "capture",
    name: { en: "Ingredients matched for you", es: "Ingredientes reconocidos" },
    summary: {
      en: "Ingredient names are matched to the ones you already use, and you are told what changed.",
      es: "Los nombres de los ingredientes se emparejan con los que ya usas, y se te dice qué cambió.",
    },
    stories: ["S-018"],
    status: "available",
  },
  {
    id: "capture-units",
    group: "capture",
    name: { en: "Your own units", es: "Tus propias unidades" },
    summary: {
      en: "A unit the app does not know is confirmed by you once, then used from then on.",
      es: "Una unidad que la app no conoce la confirmas una vez y se usa de ahí en adelante.",
    },
    stories: ["S-055"],
    status: "available",
  },
  {
    id: "capture-quick-add",
    group: "capture",
    name: { en: "Quick add", es: "Añadir rápido" },
    summary: {
      en: "Add a recipe from any screen of the app, without leaving what you are doing.",
      es: "Añade una receta desde cualquier pantalla de la app, sin dejar lo que estás haciendo.",
    },
    stories: ["S-069"],
    status: "available",
  },

  // 2. Your recipe notebooks
  {
    id: "notebooks-personal",
    group: "notebooks",
    name: { en: "Personal notebooks", es: "Cuadernos personales" },
    summary: {
      en: "Start with your own notebook, then create, rename or delete as many as you like.",
      es: "Empieza con tu propio cuaderno y crea, renombra o borra todos los que quieras.",
    },
    stories: ["S-056", "S-059", "S-060"],
    status: "available",
  },
  {
    id: "notebooks-recipe-page",
    group: "notebooks",
    name: { en: "Recipe pages with a picture", es: "Recetas con imagen" },
    summary: {
      en: "Each recipe has its own page with a picture, and you can edit or delete it.",
      es: "Cada receta tiene su propia página con una imagen, y puedes editarla o borrarla.",
    },
    stories: ["S-027", "S-067"],
    status: "available",
  },
  {
    id: "notebooks-scale",
    group: "notebooks",
    name: { en: "Scale servings", es: "Ajusta las porciones" },
    summary: {
      en: "Change the number of servings and every amount changes with it.",
      es: "Cambia el número de porciones y todas las cantidades cambian con él.",
    },
    stories: ["S-062"],
    status: "available",
  },
  {
    id: "notebooks-find",
    group: "notebooks",
    name: { en: "Find any recipe", es: "Encuentra cualquier receta" },
    summary: {
      en: "Filter by text, sort and search your recipes in clear tables.",
      es: "Filtra por texto, ordena y busca tus recetas en tablas claras.",
    },
    stories: ["S-021", "S-066"],
    status: "available",
  },

  // 3. Cook together
  {
    id: "together-kitchens",
    group: "together",
    name: { en: "Kitchens, shared or solo", es: "Cocinas, compartidas o solo tuyas" },
    summary: {
      en: "Cook on your own or invite the people you share meals with by email.",
      es: "Cocina por tu cuenta o invita por correo a quienes comparten tus comidas.",
    },
    stories: ["S-009", "S-011"],
    status: "available",
  },
  {
    id: "together-kitchen-notebooks",
    group: "together",
    name: { en: "Kitchen notebooks", es: "Cuadernos de la cocina" },
    summary: {
      en: "Notebooks every member of the kitchen can read and write.",
      es: "Cuadernos que todos los miembros de la cocina pueden leer y escribir.",
    },
    stories: ["S-056"],
    status: "available",
  },
  {
    id: "together-share-notebook",
    group: "together",
    name: { en: "Share a notebook", es: "Comparte un cuaderno" },
    summary: {
      en: "Invite someone to one of your personal notebooks to add recipes with you.",
      es: "Invita a alguien a uno de tus cuadernos personales para añadir recetas contigo.",
    },
    stories: ["S-057"],
    status: "available",
  },
  {
    id: "together-notebook-copy",
    group: "together",
    name: { en: "Bring a notebook to a kitchen", es: "Lleva un cuaderno a una cocina" },
    summary: {
      en: "Add a copy of one of your personal notebooks to a kitchen.",
      es: "Añade a una cocina una copia de uno de tus cuadernos personales.",
    },
    stories: ["S-035"],
    status: "available",
  },
  {
    id: "together-send-recipe",
    group: "together",
    name: { en: "Send a recipe", es: "Envía una receta" },
    summary: {
      en: "Send a recipe to someone, and it lands in their notebook.",
      es: "Envía una receta a alguien y llega a su cuaderno.",
    },
    stories: ["S-071"],
    status: "available",
  },

  // 4. Plan the week and shop
  {
    id: "shop-cart",
    group: "shop",
    name: { en: "Plan with the cart", es: "Planea con el carrito" },
    summary: {
      en: "Pick the week's recipes and set how many people and meals each one is for.",
      es: "Elige las recetas de la semana e indica para cuántas personas y comidas es cada una.",
    },
    stories: ["S-022"],
    status: "available",
  },
  {
    id: "shop-list",
    group: "shop",
    name: { en: "One shopping list", es: "Una sola lista de compras" },
    summary: {
      en: "Amounts are added up on one line, and each line shows the recipes it is for.",
      es: "Las cantidades se suman en una línea, y cada línea muestra para qué recetas es.",
    },
    stories: ["S-023"],
    status: "available",
  },
  {
    id: "shop-saved-list",
    group: "shop",
    name: { en: "A list that keeps", es: "Una lista que se guarda" },
    summary: {
      en: "Your list is saved, takes items you add by hand, and is closed when you are done.",
      es: "Tu lista se guarda, acepta lo que añades a mano y se cierra cuando terminas.",
    },
    stories: ["S-025"],
    status: "available",
  },
  {
    id: "shop-by-place",
    group: "shop",
    name: { en: "Shop place by place", es: "Compra lugar por lugar" },
    summary: {
      en: "Choose where you buy each ingredient, get one tab per place and mark items as bought.",
      es: "Elige dónde compras cada ingrediente, ten una pestaña por lugar y marca lo que ya compraste.",
    },
    stories: ["S-070"],
    status: "available",
  },
  {
    id: "shop-export",
    group: "shop",
    name: { en: "Export the shopping list", es: "Exporta la lista de compras" },
    summary: {
      en: "Copy your list as Markdown or download it as a PDF, for any list you saved.",
      es: "Copia tu lista en Markdown o descárgala en PDF, de cualquier lista que hayas guardado.",
    },
    stories: ["S-024"],
    status: "available",
  },

  // 5. Ingredients that stay tidy
  {
    id: "ingredients-catalog",
    group: "ingredients",
    name: { en: "An ingredient list per notebook", es: "Una lista de ingredientes por cuaderno" },
    summary: {
      en: "Each notebook keeps its own list of ingredient names, so recipes use the same words.",
      es: "Cada cuaderno guarda su propia lista de ingredientes, para que las recetas usen las mismas palabras.",
    },
    stories: ["S-018", "S-020"],
    status: "available",
  },
  {
    id: "ingredients-names",
    group: "ingredients",
    name: { en: "Rename, merge and split", es: "Renombra, une y separa" },
    summary: {
      en: "Fix an ingredient's name, join two names into one, or split them apart again.",
      es: "Corrige el nombre de un ingrediente, une dos nombres en uno o vuelve a separarlos.",
    },
    stories: ["S-043"],
    status: "available",
  },
  {
    id: "ingredients-languages",
    group: "ingredients",
    name: { en: "Ingredients in two languages", es: "Ingredientes en dos idiomas" },
    summary: {
      en: "Each ingredient has an English and a Spanish name, shown in your language.",
      es: "Cada ingrediente tiene un nombre en inglés y otro en español, y ves el de tu idioma.",
    },
    stories: ["S-043", "S-073"],
    status: "available",
  },

  // 6. Made for your home
  {
    id: "home-language",
    group: "home",
    name: { en: "Spanish or English", es: "Español o inglés" },
    summary: {
      en: "Every screen is translated; switch language whenever you want.",
      es: "Todas las pantallas están traducidas; cambia de idioma cuando quieras.",
    },
    stories: ["S-063"],
    status: "available",
  },
  {
    id: "home-profile",
    group: "home",
    name: { en: "Your profile and look", es: "Tu perfil y tu estilo" },
    summary: {
      en: "Choose your name and photo, and a light or dark look.",
      es: "Elige tu nombre y tu foto, y un aspecto claro u oscuro.",
    },
    stories: ["S-005"],
    status: "available",
  },

  // Planned: shown only in the "Coming soon" strip (FR-004).
  {
    id: "planned-assistant",
    group: "notebooks",
    name: { en: "Kitchen assistant", es: "Asistente de cocina" },
    summary: {
      en: "Ask questions about your recipes and get answers from them.",
      es: "Haz preguntas sobre tus recetas y obtén respuestas a partir de ellas.",
    },
    stories: ["S-029", "S-030"],
    status: "planned",
  },
  {
    id: "planned-meaning-search",
    group: "notebooks",
    name: { en: "Search by meaning", es: "Búsqueda por significado" },
    summary: {
      en: "Find recipes by what you mean, not only by the words they use.",
      es: "Encuentra recetas por lo que quieres decir, no solo por sus palabras.",
    },
    stories: ["S-044"],
    status: "planned",
  },
  {
    id: "planned-recipe-pdf",
    group: "notebooks",
    name: { en: "Recipe PDF", es: "Receta en PDF" },
    summary: {
      en: "Save or print a recipe as a PDF.",
      es: "Guarda o imprime una receta en PDF.",
    },
    stories: ["S-028"],
    status: "planned",
  },
  {
    id: "planned-receipts",
    group: "shop",
    name: { en: "Check off with a receipt", es: "Marca con el recibo" },
    summary: {
      en: "Paste a receipt to mark what you already bought.",
      es: "Pega un recibo para marcar lo que ya compraste.",
    },
    stories: ["S-068"],
    status: "planned",
  },
];

/** The six groups, in the order a person uses the app. */
export function groupsInOrder(): readonly FeatureGroup[] {
  return [...featureGroups].sort((a, b) => a.order - b.order);
}

/** A group's available features, in inventory order. */
export function availableFeatures(group: GroupId): readonly Feature[] {
  return features.filter((feature) => feature.group === group && feature.status === "available");
}

/** Every planned feature, in inventory order. */
export function plannedFeatures(): readonly Feature[] {
  return features.filter((feature) => feature.status === "planned");
}
