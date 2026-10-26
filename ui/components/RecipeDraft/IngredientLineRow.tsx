"use client";

import { BackIcon, TrashIcon } from "@/app/icons";
import { Tooltip } from "@/components/Tooltip";
import type { DraftErrors } from "@/lib/capture/draftRules";
import type { LineView } from "@/lib/capture/captureStore";
import { captureMessages } from "@/lib/i18n/capture";

type IngredientLineRowProps = {
  line: LineView;
  index: number;
  count: number;
  errors: NonNullable<DraftErrors["lines"][number]>;
  units: string[];
  sizes: string[];
  onChange: (next: LineView) => void;
  onRemove: () => void;
  onMove: (direction: -1 | 1) => void;
};

/** One bordered box holds several fields; the fields inside only add dividers. */
const groupClassName =
  "flex min-w-0 items-stretch divide-x divide-border overflow-hidden rounded-[0.6rem] border border-border bg-background focus-within:border-foreground/50";

const fieldClassName =
  "min-w-0 border-0 bg-transparent px-2 py-[0.3rem] text-[0.9rem] text-foreground outline-none";

const iconButtonClassName =
  "flex h-8 w-8 items-center justify-center rounded-[0.5rem] text-muted disabled:opacity-40";

/**
 * One ingredient line (spec 016 FR-007 to FR-012). The left column holds two boxes: name, quantity,
 * unit and size (size only for the unit "unit"), then preparation and note. The right column is a
 * 2×2 grid, one row per box: vague and remove on top, move up and down below. Fields are labelled
 * for screen readers only. A vague amount clears the quantity and the unit. Errors show under the row.
 */
export function IngredientLineRow({
  line,
  index,
  count,
  errors,
  units,
  sizes,
  onChange,
  onRemove,
  onMove,
}: IngredientLineRowProps) {
  const sizeEnabled = line.unit === "unit";

  return (
    <li className="border-b border-border py-3">
      <div className="flex items-stretch gap-2">
        <div className="flex min-w-0 flex-1 flex-col gap-2">
          <div className={groupClassName}>
            <input
              aria-label={captureMessages.ingredientName}
              placeholder={captureMessages.ingredientName}
              className={`${fieldClassName} flex-1`}
              value={line.name}
              onChange={(event) => onChange({ ...line, name: event.target.value })}
            />
            <input
              type="number"
              min="0"
              step="any"
              aria-label={captureMessages.quantity}
              placeholder={captureMessages.quantity}
              className={`${fieldClassName} w-24 shrink-0`}
              value={line.quantity ?? ""}
              disabled={line.vague}
              onChange={(event) =>
                onChange({
                  ...line,
                  quantity: event.target.value === "" ? null : Number(event.target.value),
                })
              }
            />
            <select
              aria-label={captureMessages.unit}
              className={`${fieldClassName} shrink-0`}
              value={line.unit ?? ""}
              disabled={line.vague}
              onChange={(event) =>
                onChange({
                  ...line,
                  unit: event.target.value === "" ? null : event.target.value,
                  size: event.target.value === "unit" ? line.size : null,
                })
              }
            >
              <option value="">—</option>
              {units.map((unit) => (
                <option key={unit} value={unit}>
                  {unit}
                </option>
              ))}
            </select>
            {sizeEnabled ? (
              <select
                aria-label={captureMessages.size}
                className={`${fieldClassName} shrink-0`}
                value={line.size ?? ""}
                onChange={(event) =>
                  onChange({ ...line, size: event.target.value === "" ? null : event.target.value })
                }
              >
                <option value="">—</option>
                {sizes.map((size) => (
                  <option key={size} value={size}>
                    {size}
                  </option>
                ))}
              </select>
            ) : null}
          </div>

          <div className={groupClassName}>
            <input
              aria-label={captureMessages.preparation}
              placeholder={captureMessages.preparation}
              className={`${fieldClassName} flex-1`}
              value={line.preparation ?? ""}
              onChange={(event) => onChange({ ...line, preparation: event.target.value || null })}
            />
            <input
              aria-label={captureMessages.note}
              placeholder={captureMessages.note}
              className={`${fieldClassName} flex-1`}
              value={line.note ?? ""}
              onChange={(event) => onChange({ ...line, note: event.target.value || null })}
            />
          </div>
        </div>

        <div className="grid shrink-0 grid-cols-2 grid-rows-2 place-items-center gap-1">
          <Tooltip label={captureMessages.vague}>
            <input
              type="checkbox"
              aria-label={captureMessages.vague}
              checked={line.vague}
              onChange={(event) =>
                onChange(
                  event.target.checked
                    ? { ...line, vague: true, quantity: null, unit: null, size: null }
                    : { ...line, vague: false },
                )
              }
            />
          </Tooltip>
          <button
            type="button"
            onClick={onRemove}
            aria-label={captureMessages.remove}
            title={captureMessages.remove}
            className={iconButtonClassName}
          >
            <TrashIcon className="h-4 w-4" />
          </button>
          <button
            type="button"
            onClick={() => onMove(-1)}
            disabled={index === 0}
            aria-label={captureMessages.moveUp}
            title={captureMessages.moveUp}
            className={iconButtonClassName}
          >
            <BackIcon className="size-4 rotate-90" />
          </button>
          <button
            type="button"
            onClick={() => onMove(1)}
            disabled={index === count - 1}
            aria-label={captureMessages.moveDown}
            title={captureMessages.moveDown}
            className={iconButtonClassName}
          >
            <BackIcon className="size-4 -rotate-90" />
          </button>
        </div>
      </div>

      {errors.map((code) => (
        <p key={code} role="alert" className="m-0 mt-2 text-[0.8rem] text-owe">
          {captureMessages.errors[code]}
        </p>
      ))}
    </li>
  );
}
