/** The label in `language`, or in the other language when that one is missing (spec 016 FR-011). */
export function pickLabel(labels: { en?: string; es?: string }, language: "en" | "es"): string {
  const other = language === "en" ? "es" : "en";
  return labels[language] || labels[other] || "";
}
