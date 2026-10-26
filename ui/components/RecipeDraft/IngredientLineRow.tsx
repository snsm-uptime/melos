"use client";

import type { LineView } from "@/lib/capture/captureStore";
import { captureMessages } from "@/lib/i18n/capture";
import type { DraftErrors } from "@/lib/capture/draftRules";

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

const fieldClassName =
  "w-full rounded-[0.6rem] border border-border bg-background px-2 py-[0.35rem] text-[0.9rem] text-foreground";

/**
 * One ingredient line (spec 016 FR-007 to FR-012). A vague amount clears the quantity and the
 * unit. Size is offered only with the unit "unit". Errors show under the row.
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
    <li className="flex flex-col gap-2 border-b border-border py-3">
      <div className="grid grid-cols-2 gap-2">
        <label className="col-span-2 flex flex-col gap-1 text-[0.8rem] text-muted">
          {captureMessages.ingredientName}
          <input
            className={fieldClassName}
            value={line.name}
            onChange={(event) => onChange({ ...line, name: event.target.value })}
          />
        </label>
        <label className="flex flex-col gap-1 text-[0.8rem] text-muted">
          {captureMessages.quantity}
          <input
            type="number"
            min="0"
            step="any"
            className={fieldClassName}
            value={line.quantity ?? ""}
            disabled={line.vague}
            onChange={(event) =>
              onChange({
                ...line,
                quantity: event.target.value === "" ? null : Number(event.target.value),
              })
            }
          />
        </label>
        <label className="flex flex-col gap-1 text-[0.8rem] text-muted">
          {captureMessages.unit}
          <select
            className={fieldClassName}
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
        </label>
        <label className="flex flex-col gap-1 text-[0.8rem] text-muted">
          {captureMessages.size}
          <select
            className={fieldClassName}
            value={line.size ?? ""}
            disabled={!sizeEnabled}
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
        </label>
        <label className="flex flex-col gap-1 text-[0.8rem] text-muted">
          {captureMessages.preparation}
          <input
            className={fieldClassName}
            value={line.preparation ?? ""}
            onChange={(event) =>
              onChange({ ...line, preparation: event.target.value || null })
            }
          />
        </label>
        <label className="col-span-2 flex flex-col gap-1 text-[0.8rem] text-muted">
          {captureMessages.note}
          <input
            className={fieldClassName}
            value={line.note ?? ""}
            onChange={(event) => onChange({ ...line, note: event.target.value || null })}
          />
        </label>
        <label className="col-span-2 flex items-center gap-2 text-[0.85rem] text-muted">
          <input
            type="checkbox"
            checked={line.vague}
            onChange={(event) =>
              onChange(
                event.target.checked
                  ? { ...line, vague: true, quantity: null, unit: null, size: null }
                  : { ...line, vague: false },
              )
            }
          />
          {captureMessages.vague}
        </label>
      </div>
      {errors.map((code) => (
        <p key={code} role="alert" className="m-0 text-[0.8rem] text-owe">
          {captureMessages.errors[code]}
        </p>
      ))}
      <div className="flex gap-2 text-[0.8rem]">
        <button type="button" onClick={() => onMove(-1)} disabled={index === 0} className="text-muted">
          {captureMessages.moveUp}
        </button>
        <button
          type="button"
          onClick={() => onMove(1)}
          disabled={index === count - 1}
          className="text-muted"
        >
          {captureMessages.moveDown}
        </button>
        <button type="button" onClick={onRemove} className="text-muted">
          {captureMessages.remove}
        </button>
      </div>
    </li>
  );
}
