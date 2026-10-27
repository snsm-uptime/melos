"use client";

import { useId, useState } from "react";

import { BackIcon, CloseIcon } from "@/app/icons";
import { Card, CardBody, CardHeader } from "@/components/Card";
import type { DraftErrors } from "@/lib/capture/draftRules";
import { chooseLineMatch, NEW_CHOICE, type LineView } from "@/lib/capture/captureStore";
import { captureMessages } from "@/lib/i18n/capture";

type IngredientLineRowProps = {
  line: LineView;
  index: number;
  count: number;
  errors: NonNullable<DraftErrors["lines"][number]>;
  units: string[];
  sizes: string[];
  /** The notebook's catalog entries, for the match control (spec 018 FR-005). */
  catalog: string[];
  onChange: (next: LineView) => void;
  onRemove: () => void;
  onMove: (direction: -1 | 1) => void;
};

/** Borderless fields that read as text; a faint fill shows on hover and focus. */
const fieldClassName =
  "min-w-0 rounded-[0.4rem] border-0 bg-transparent px-1 py-[0.15rem] text-foreground outline-none hover:bg-background focus:bg-background disabled:opacity-40";

const headingClassName = "text-[1.05rem] font-semibold";

const amountClassName = `${fieldClassName} ${headingClassName} shrink-0 text-accent`;

const labelClassName = "m-0 w-24 shrink-0 text-[0.8rem] font-medium text-muted";

const iconButtonClassName =
  "flex h-7 w-7 items-center justify-center rounded-[0.5rem] text-muted hover:text-foreground disabled:opacity-40";

/**
 * One ingredient line (spec 016 FR-007 to FR-012). The name and the amount (quantity, unit, and size
 * for the unit "unit") share the top line, then the catalog match and vague toggle. Below are
 * labelled preparation and note. The bottom bar holds remove and the move buttons. A vague amount
 * clears the quantity and the unit. Errors show under the row.
 */
export function IngredientLineRow({
  line,
  index,
  count,
  errors,
  units,
  sizes,
  catalog,
  onChange,
  onRemove,
  onMove,
}: IngredientLineRowProps) {
  const sizeEnabled = line.unit === "unit";
  const matchedEntry = line.match.kind === "matched" ? line.match.entry : null;
  const id = useId();
  const preparationId = `${id}-preparation`;
  const noteId = `${id}-note`;
  const vagueId = `${id}-vague`;

  /** Cache for quantity, unit, size when vague is toggled — restores on uncheck.
   * Tied to line.key so the cache is invalidated when the line changes externally. */
  const [cachedAmount, setCachedAmount] = useState<{
    lineKey: string;
    quantity: number | null;
    unit: string | null;
    size: string | null;
  } | null>(null);

  return (
    <Card as="li">
      <CardHeader className="flex flex-col gap-1">
        <div className="flex items-center justify-between gap-2">
          <input
            aria-label={captureMessages.ingredientName}
            placeholder={captureMessages.ingredientName}
            className={`${fieldClassName} ${headingClassName} flex-1`}
            value={line.name}
            onChange={(event) => onChange({ ...line, name: event.target.value })}
          />
          <div className="flex shrink-0 items-center">
            <input
              type="number"
              min="0"
              step="any"
              aria-label={captureMessages.quantity}
              placeholder="0"
              className={`${amountClassName} w-16 text-right [appearance:textfield] [&::-webkit-inner-spin-button]:appearance-none [&::-webkit-outer-spin-button]:appearance-none`}
              value={line.quantity ?? ""}
              disabled={line.vague}
              onChange={(event) => {
                setCachedAmount(null);
                onChange({
                  ...line,
                  quantity: event.target.value === "" ? null : Number(event.target.value),
                });
              }}
            />
            <select
              aria-label={captureMessages.unit}
              className={amountClassName}
              value={line.unit ?? ""}
              disabled={line.vague}
              onChange={(event) => {
                setCachedAmount(null);
                onChange({
                  ...line,
                  unit: event.target.value === "" ? null : event.target.value,
                  size: event.target.value === "unit" ? line.size : null,
                });
              }}
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
                className={amountClassName}
                value={line.size ?? ""}
                onChange={(event) => {
                  setCachedAmount(null);
                  onChange({
                    ...line,
                    size: event.target.value === "" ? null : event.target.value,
                  });
                }}
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
        </div>

        <div className="flex items-center justify-between gap-2">
          <select
            aria-label={captureMessages.matchControl}
            className={`${fieldClassName} text-[0.8rem] text-muted`}
            value={matchedEntry ?? NEW_CHOICE}
            onChange={(event) => onChange(chooseLineMatch(line, event.target.value))}
          >
            <option value={NEW_CHOICE}>{captureMessages.newIngredient}</option>
            {catalog.map((entry) => (
              <option key={entry} value={entry}>
                {entry}
              </option>
            ))}
          </select>

          <label htmlFor={vagueId} className="flex shrink-0 items-center gap-2 text-[0.8rem] text-muted">
            <input
              id={vagueId}
              type="checkbox"
              checked={line.vague}
              onChange={(event) => {
                if (event.target.checked) {
                  // Checking: cache current values and clear them
                  setCachedAmount({
                    lineKey: line.key,
                    quantity: line.quantity,
                    unit: line.unit,
                    size: line.size,
                  });
                  onChange({
                    ...line,
                    vague: true,
                    quantity: null,
                    unit: null,
                    size: null,
                  });
                } else {
                  // Unchecking: restore cached values if available and still valid
                  const canRestore =
                    cachedAmount && cachedAmount.lineKey === line.key;
                  onChange({
                    ...line,
                    vague: false,
                    ...(canRestore && {
                      quantity: cachedAmount.quantity,
                      unit: cachedAmount.unit,
                      size: cachedAmount.size,
                    }),
                  });
                  setCachedAmount(null);
                }
              }}
            />
            {captureMessages.vague}
          </label>
        </div>
      </CardHeader>

      <CardBody>
        <div className="flex items-center gap-2">
          <h3 className={labelClassName}>
            <label htmlFor={preparationId}>{captureMessages.preparation}:</label>
          </h3>
          <input
            id={preparationId}
            className={`${fieldClassName} flex-1 text-[0.9rem]`}
            value={line.preparation ?? ""}
            onChange={(event) => onChange({ ...line, preparation: event.target.value || null })}
          />
        </div>

        <div className="flex items-center gap-2">
          <h3 className={labelClassName}>
            <label htmlFor={noteId}>{captureMessages.note}:</label>
          </h3>
          <input
            id={noteId}
            className={`${fieldClassName} flex-1 text-[0.9rem]`}
            value={line.note ?? ""}
            onChange={(event) => onChange({ ...line, note: event.target.value || null })}
          />
        </div>

        <div className="mt-1 flex items-center justify-between gap-2">
          <button
            type="button"
            onClick={onRemove}
            aria-label={captureMessages.remove}
            title={captureMessages.remove}
            className={iconButtonClassName}
          >
            <CloseIcon className="h-4 w-4" />
          </button>
          <div className="flex items-center gap-1">
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
          <p key={code} role="alert" className="m-0 text-[0.8rem] text-owe">
            {captureMessages.errors[code]}
          </p>
        ))}
      </CardBody>
    </Card>
  );
}
