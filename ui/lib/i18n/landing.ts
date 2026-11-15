/**
 * The signed-out landing page, EN/ES (spec 063): the feature tour of spec 075. Feature names and
 * group texts live in lib/featureInventory.ts; this file holds the rest of the page and the
 * invented data drawn inside each demo scene (recipes, names, notebooks). The scenes are the app's
 * own components, so their labels come from the app's messages, not from here.
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
          "Two recipes in Ana's Notebook, crepes and a white sauce, go into the cart. The shopping list shows one line for flour, 1 cup + 3 tbsp, with both recipes, and a line for eggs.",
        notebook: "Ana's Notebook",
        recipeA: "Crepes",
        recipeB: "White sauce",
        flour: "flour",
        eggs: "eggs",
      },
      capture: {
        title: "A recipe becomes a draft",
        description:
          "The add-recipe choices: a link, a picture or pasted text. The pasted recipe becomes a draft to review: salt with the vague amount a pinch, and onion as 2 unit large.",
        salt: "salt",
        saltAmount: "a pinch",
        onion: "onion",
      },
      notebooks: {
        title: "Scaling a recipe from 4 to 2",
        description:
          "Ana's Notebook holds three recipes. The lentil soup opens, its servings change from 4 to 2, and every amount is halved.",
        notebook: "Ana's Notebook",
        recipes: ["Lentil soup", "Tomato rice", "Crepes"],
        lines: ["lentils", "carrots", "water"],
      },
      together: {
        title: "Sending a recipe to Leo",
        description:
          "A kitchen with two members, Ana and Leo, and their notebooks. Ana sends a tomato rice recipe to Leo, and a message confirms it was sent.",
        kitchen: "Our kitchen",
        notebookAna: "Ana's Notebook",
        notebookLeo: "Leo's Notebook",
        recipe: "Tomato rice",
      },
      shop: {
        title: "Two recipes, one shopping list",
        description:
          "Crepes and a white sauce, both from Ana's Notebook, are in the cart. The shopping list shows one line, flour 1 cup + 3 tbsp, with both recipes. On the Market tab, eggs and milk are marked as bought.",
        notebook: "Ana's Notebook",
        recipeA: "Crepes",
        recipeB: "White sauce",
        flour: "flour",
        eggs: "eggs",
        milk: "milk",
        placeMarket: "Market",
        placeBakery: "Bakery",
      },
      ingredients: {
        title: "Merging two names",
        description:
          "The ingredient table has both onions and onion. They are merged into one name, onion, which keeps onions as another spelling and also shows its Spanish name, cebolla.",
        notebook: "Ana's Notebook",
        merged: "onions",
        kept: "onion",
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
          recipe: "Lentil soup",
          notebook: "Ana's Notebook",
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
          "Dos recetas del Cuaderno de Ana, unas crepas y una salsa blanca, van al carrito. La lista de compras muestra una sola línea de harina, 1 cup + 3 tbsp, con las dos recetas, y una línea de huevos.",
        notebook: "Cuaderno de Ana",
        recipeA: "Crepas",
        recipeB: "Salsa blanca",
        flour: "harina",
        eggs: "huevos",
      },
      capture: {
        title: "Una receta se vuelve borrador",
        description:
          "Las opciones para agregar una receta: un enlace, una imagen o un texto pegado. La receta pegada se vuelve un borrador para revisar: la sal con la cantidad imprecisa una pizca, y la cebolla como 2 unit large.",
        salt: "sal",
        saltAmount: "una pizca",
        onion: "cebolla",
      },
      notebooks: {
        title: "Una receta de 4 a 2 porciones",
        description:
          "El Cuaderno de Ana tiene tres recetas. Se abre la sopa de lentejas, las porciones pasan de 4 a 2 y todas las cantidades se reducen a la mitad.",
        notebook: "Cuaderno de Ana",
        recipes: ["Sopa de lentejas", "Arroz con tomate", "Crepas"],
        lines: ["lentejas", "zanahorias", "agua"],
      },
      together: {
        title: "Enviar una receta a Leo",
        description:
          "Una cocina con dos miembros, Ana y Leo, y sus cuadernos. Ana envía una receta de arroz con tomate a Leo, y un mensaje confirma que se envió.",
        kitchen: "Nuestra cocina",
        notebookAna: "Cuaderno de Ana",
        notebookLeo: "Cuaderno de Leo",
        recipe: "Arroz con tomate",
      },
      shop: {
        title: "Dos recetas, una lista de compras",
        description:
          "Unas crepas y una salsa blanca, las dos del Cuaderno de Ana, están en el carrito. La lista de compras muestra una sola línea, harina 1 cup + 3 tbsp, con las dos recetas. En la pestaña Mercado, los huevos y la leche quedan marcados como comprados.",
        notebook: "Cuaderno de Ana",
        recipeA: "Crepas",
        recipeB: "Salsa blanca",
        flour: "harina",
        eggs: "huevos",
        milk: "leche",
        placeMarket: "Mercado",
        placeBakery: "Panadería",
      },
      ingredients: {
        title: "Unir dos nombres",
        description:
          "La tabla de ingredientes tiene cebollas y cebolla. Se unen en un solo nombre, cebolla, que guarda cebollas como otra escritura y también muestra su nombre en inglés, onion.",
        notebook: "Cuaderno de Ana",
        merged: "cebollas",
        kept: "cebolla",
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
          recipe: "Sopa de lentejas",
          notebook: "Cuaderno de Ana",
        },
      },
    },
  },
} as const;

export type LandingMessages = (typeof landingMessages)[keyof typeof landingMessages];
export type DemoId = "overview" | "capture" | "notebooks" | "together" | "shop" | "ingredients" | "home";
