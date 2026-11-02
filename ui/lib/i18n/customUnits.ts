/** Custom unit question and unit picker text, EN/ES (spec 055 FR-015). */

export const customUnitMessages = {
  en: {
    question: (word: string) => `Use "${word}" as a unit from now on?`,
    yes: "Yes",
    no: "No",
    other: "Other…",
    otherLabel: "Your own unit",
    search: "Search units",
    noMatch: "No unit found",
    notAUnit: "That can't be used as a unit.",
    checkFailed: "We couldn't check that word. Try again.",
  },
  es: {
    question: (word: string) => `¿Usar "${word}" como unidad de ahora en adelante?`,
    yes: "Sí",
    no: "No",
    other: "Otra…",
    otherLabel: "Tu propia unidad",
    search: "Buscar unidad",
    noMatch: "No se encontró la unidad",
    notAUnit: "Eso no se puede usar como unidad.",
    checkFailed: "No pudimos revisar esa palabra. Inténtalo de nuevo.",
  },
} as const;
