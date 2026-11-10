/**
 * The signed-out landing page, EN/ES (spec 063): the feature tour of spec 075. Feature names and
 * group texts live in lib/featureInventory.ts; this file holds the rest of the page and the text
 * drawn inside each demo scene. Every recipe, amount and name in a scene is invented.
 */

export const landingMessages = {
  en: {
    headline: "Your home cookbook, from recipe to shopping list",
    intro:
      "Menus everyone loves to share. Melos turns recipes from text, links and cookbook photos into tidy notebooks, shares them with the people you cook with, and adds up the week's shopping list for you.",
    createAccount: "Create an account",
    signIn: "Sign in",
    indexLabel: "Jump to a section",
    featuresHeading: "What you can do",
    comingSoonTitle: "Coming soon",
    comingSoonLede: "We are working on these next.",
    closingTitle: "Ready to cook?",
    closingBody: "Create your account and save your first recipe today.",
    demo: {
      pause: "Pause demo",
      play: "Play demo",
      overview: {
        title: "Melos at work",
        description:
          "A pasted crepe recipe is captured, saved to Ana's Notebook and added to the cart with a white sauce. The shopping list shows one line, flour — 1 cup + 3 tbsp, for both recipes.",
        pasteLabel: "Pasted recipe",
        pasted: "Crepes: 1 cup flour, 2 eggs, 1 cup milk",
        captured: "Recipe captured",
        savedTo: "Saved to Ana's Notebook",
        addedToCart: "Added to the cart",
        listTitle: "Shopping list",
        recipeA: "Crepes",
        recipeB: "White sauce",
        flourLine: "flour — 1 cup + 3 tbsp",
        eggsLine: "eggs — 2",
      },
      capture: {
        title: "A pasted recipe becomes a draft",
        description:
          "Text, a link or a photo can start a recipe. Pasted text with a pinch of salt and 2 large onions becomes a draft: salt is marked as a vague amount, and onion reads 2 unit large, ready to review before saving.",
        sourceText: "Text",
        sourceLink: "Link",
        sourcePhoto: "Photo",
        pastedSalt: "a pinch of salt",
        pastedOnion: "2 large onions",
        draftTitle: "Draft",
        salt: "salt",
        saltNote: "a pinch",
        vague: "Vague amount",
        onion: "onion",
        onionAmount: "2 unit large",
        review: "Review and save",
      },
      notebooks: {
        title: "Scaling a recipe from 4 to 2",
        description:
          "Ana's Notebook holds three recipes. The lentil soup opens, its servings change from 4 to 2, and every amount is halved.",
        notebook: "Ana's Notebook",
        recipes: ["Lentil soup", "Tomato rice", "Crepes"],
        servings: "Servings",
        lines: [
          { name: "lentils", before: "2 cups", after: "1 cup" },
          { name: "carrots", before: "4 unit", after: "2 unit" },
          { name: "water", before: "6 cups", after: "3 cups" },
        ],
      },
      together: {
        title: "Sending a recipe to Leo",
        description:
          "A kitchen with two members, Ana and Leo, and their notebooks. Ana sends a tomato rice recipe to Leo, and a message confirms it was sent.",
        kitchen: "Our kitchen",
        members: "Members",
        notebookAna: "Ana's Notebook",
        notebookLeo: "Leo's Notebook",
        recipe: "Tomato rice",
        send: "Send to Leo",
        sent: "Sent to Leo",
      },
      shop: {
        title: "Two recipes, one shopping list",
        description:
          "Crepes with 1 cup of flour and a white sauce with 3 tablespoons of flour go into the cart. The shopping list shows one line, flour — 1 cup + 3 tbsp, with both recipes. On the Market tab, eggs and milk are marked as bought.",
        cart: "Cart",
        recipeA: "Crepes",
        recipeB: "White sauce",
        flourA: "1 cup flour",
        flourB: "3 tbsp flour",
        listTitle: "Shopping list",
        placeMarket: "Market",
        placeBakery: "Bakery",
        flourLine: "flour — 1 cup + 3 tbsp",
        eggsLine: "eggs — 2",
        milkLine: "milk — 2 cups",
        bought: "Bought",
      },
      ingredients: {
        title: "Merging two names",
        description:
          "The ingredient list has both onions and onion. They are merged into one name, onion, which also shows its Spanish name, cebolla.",
        catalog: "Ingredients",
        merged: "onions",
        kept: "onion",
        merge: "Merge",
        mergedNote: "“onions” is now another name for “onion”",
        variantLabel: "Spanish",
        variant: "cebolla",
      },
      home: {
        title: "One screen, two languages, two looks",
        description:
          "The same recipe card shown in Spanish with a light look and in English with a dark look.",
        light: "Light",
        dark: "Dark",
        /** Drawn in this language on both pages: the scene shows the card in each language. */
        card: {
          language: "English",
          recipe: "Lentil soup",
          servings: "4 servings",
          line: "lentils — 2 cups",
          action: "Add to cart",
        },
      },
    },
  },
  es: {
    headline: "Tu recetario de casa, de la receta a la lista de compras",
    intro:
      "Menús que todos quieren compartir. Melos convierte recetas de texto, enlaces y fotos de libros en cuadernos ordenados, las comparte con quienes cocinas y suma por ti la lista de compras de la semana.",
    createAccount: "Crear una cuenta",
    signIn: "Iniciar sesión",
    indexLabel: "Ir a una sección",
    featuresHeading: "Lo que puedes hacer",
    comingSoonTitle: "Próximamente",
    comingSoonLede: "Estamos trabajando en esto.",
    closingTitle: "¿Listos para cocinar?",
    closingBody: "Crea tu cuenta y guarda tu primera receta hoy.",
    demo: {
      pause: "Pausar la demostración",
      play: "Reproducir la demostración",
      overview: {
        title: "Melos en acción",
        description:
          "Una receta de crepas pegada se guarda en el Cuaderno de Ana y se añade al carrito con una salsa blanca. La lista de compras muestra una sola línea, harina — 1 taza + 3 cdas, para las dos recetas.",
        pasteLabel: "Receta pegada",
        pasted: "Crepas: 1 taza de harina, 2 huevos, 1 taza de leche",
        captured: "Receta guardada",
        savedTo: "Guardada en el Cuaderno de Ana",
        addedToCart: "Añadida al carrito",
        listTitle: "Lista de compras",
        recipeA: "Crepas",
        recipeB: "Salsa blanca",
        flourLine: "harina — 1 taza + 3 cdas",
        eggsLine: "huevos — 2",
      },
      capture: {
        title: "Una receta pegada se vuelve borrador",
        description:
          "Un texto, un enlace o una foto pueden empezar una receta. Un texto con una pizca de sal y 2 cebollas grandes se vuelve un borrador: la sal queda como cantidad imprecisa y la cebolla dice 2 unidad grande, lista para revisar antes de guardar.",
        sourceText: "Texto",
        sourceLink: "Enlace",
        sourcePhoto: "Foto",
        pastedSalt: "una pizca de sal",
        pastedOnion: "2 cebollas grandes",
        draftTitle: "Borrador",
        salt: "sal",
        saltNote: "una pizca",
        vague: "Cantidad imprecisa",
        onion: "cebolla",
        onionAmount: "2 unidad grande",
        review: "Revisar y guardar",
      },
      notebooks: {
        title: "Una receta de 4 a 2 porciones",
        description:
          "El Cuaderno de Ana tiene tres recetas. Se abre la sopa de lentejas, las porciones pasan de 4 a 2 y todas las cantidades se reducen a la mitad.",
        notebook: "Cuaderno de Ana",
        recipes: ["Sopa de lentejas", "Arroz con tomate", "Crepas"],
        servings: "Porciones",
        lines: [
          { name: "lentejas", before: "2 tazas", after: "1 taza" },
          { name: "zanahorias", before: "4 unidad", after: "2 unidad" },
          { name: "agua", before: "6 tazas", after: "3 tazas" },
        ],
      },
      together: {
        title: "Enviar una receta a Leo",
        description:
          "Una cocina con dos miembros, Ana y Leo, y sus cuadernos. Ana envía una receta de arroz con tomate a Leo, y un mensaje confirma que se envió.",
        kitchen: "Nuestra cocina",
        members: "Miembros",
        notebookAna: "Cuaderno de Ana",
        notebookLeo: "Cuaderno de Leo",
        recipe: "Arroz con tomate",
        send: "Enviar a Leo",
        sent: "Enviada a Leo",
      },
      shop: {
        title: "Dos recetas, una lista de compras",
        description:
          "Unas crepas con 1 taza de harina y una salsa blanca con 3 cucharadas de harina van al carrito. La lista de compras muestra una sola línea, harina — 1 taza + 3 cdas, con las dos recetas. En la pestaña Mercado, los huevos y la leche quedan marcados como comprados.",
        cart: "Carrito",
        recipeA: "Crepas",
        recipeB: "Salsa blanca",
        flourA: "1 taza de harina",
        flourB: "3 cdas de harina",
        listTitle: "Lista de compras",
        placeMarket: "Mercado",
        placeBakery: "Panadería",
        flourLine: "harina — 1 taza + 3 cdas",
        eggsLine: "huevos — 2",
        milkLine: "leche — 2 tazas",
        bought: "Comprado",
      },
      ingredients: {
        title: "Unir dos nombres",
        description:
          "La lista de ingredientes tiene cebollas y cebolla. Se unen en un solo nombre, cebolla, que también muestra su nombre en inglés, onion.",
        catalog: "Ingredientes",
        merged: "cebollas",
        kept: "cebolla",
        merge: "Unir",
        mergedNote: "«cebollas» ahora es otro nombre de «cebolla»",
        variantLabel: "Inglés",
        variant: "onion",
      },
      home: {
        title: "Una pantalla, dos idiomas, dos estilos",
        description:
          "La misma tarjeta de receta en español con aspecto claro y en inglés con aspecto oscuro.",
        light: "Claro",
        dark: "Oscuro",
        /** Drawn in this language on both pages: the scene shows the card in each language. */
        card: {
          language: "Español",
          recipe: "Sopa de lentejas",
          servings: "4 porciones",
          line: "lentejas — 2 tazas",
          action: "Añadir al carrito",
        },
      },
    },
  },
} as const;

export type LandingMessages = (typeof landingMessages)[keyof typeof landingMessages];
export type DemoId = "overview" | "capture" | "notebooks" | "together" | "shop" | "ingredients" | "home";
