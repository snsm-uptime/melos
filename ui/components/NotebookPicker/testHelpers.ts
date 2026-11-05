import { act } from "react";

/** Test helpers for NotebookPicker (a SearchableSelect, not a native select). */
export function notebookPicker(label = "Notebook"): HTMLButtonElement | null {
  return document.querySelector(`button[aria-label="${label}"]`);
}

/** The notebook shown as chosen. */
export function pickedNotebook(label?: string): string | null {
  return notebookPicker(label)?.textContent ?? null;
}

/** Every notebook the picker offers, in order; the picker is left closed. */
export function notebookChoices(label?: string): string[] {
  act(() => notebookPicker(label)!.click());
  const names = Array.from(document.querySelectorAll('[role="option"]')).map(
    (option) => option.textContent ?? "",
  );
  act(() => notebookPicker(label)!.click());
  return names;
}

/** Opens the picker and chooses the notebook named `name`. */
export function pickNotebook(name: string, label?: string): void {
  act(() => notebookPicker(label)!.click());
  const option = Array.from(document.querySelectorAll<HTMLElement>('[role="option"]')).find(
    (item) => item.textContent === name,
  );
  act(() => option!.click());
}
