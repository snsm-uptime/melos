/** Client helpers for recipe lists via the same-origin BFF (spec 021 routes). */

import { getJson, type NotebookResult } from "@/lib/notebooksClient";

export type RecipeCard = {
  id: string;
  title: string;
  author_alias: string | null;
  ingredient_count: number;
  notebook_id: string;
  notebook_name: string;
  created_at: string;
};

export type RecipePage = {
  items: RecipeCard[];
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
};

function isCard(row: unknown): row is RecipeCard {
  if (!row || typeof row !== "object") return false;
  const card = row as Partial<Record<keyof RecipeCard, unknown>>;
  return (
    typeof card.id === "string" &&
    typeof card.title === "string" &&
    typeof card.ingredient_count === "number" &&
    typeof card.notebook_name === "string"
  );
}

function asPage(data: unknown): RecipePage | null {
  if (!data || typeof data !== "object") return null;
  const page = data as Partial<Record<keyof RecipePage, unknown>>;
  if (
    !Array.isArray(page.items) ||
    typeof page.page !== "number" ||
    typeof page.total_pages !== "number" ||
    typeof page.total !== "number"
  ) {
    return null;
  }
  if (!page.items.every(isCard)) return null;
  return data as RecipePage;
}

function query(page: number, q: string): string {
  const params = new URLSearchParams({ page: String(page) });
  if (q.trim()) params.set("q", q);
  return params.toString();
}

export function fetchNotebookRecipes(
  notebookId: string,
  page: number,
  q: string,
): Promise<NotebookResult<RecipePage>> {
  return getJson(
    `/api/notebooks/${encodeURIComponent(notebookId)}/recipes?${query(page, q)}`,
    asPage,
  );
}

export function fetchKitchenRecipes(
  kitchenId: string,
  page: number,
  q: string,
): Promise<NotebookResult<RecipePage>> {
  return getJson(
    `/api/notebooks/kitchens/${encodeURIComponent(kitchenId)}/recipes?${query(page, q)}`,
    asPage,
  );
}
