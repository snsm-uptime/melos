"use client";

import { useEffect, useId, useRef, useState } from "react";

import { formatQuantity } from "@/lib/recipeLines";

import { Card, CardBody, CardHeader } from "@/components/Card";
import { SearchableSelect } from "@/components/soft-ledger/SearchableSelect";
import type { DraftErrors } from "@/lib/capture/draftRules";
import {
  chooseLineMatch,
  NEW_CHOICE,
  type LineView,
} from "@/lib/capture/captureStore";
import type { NameChange } from "@/lib/capture/nameChanges";
import { customUnitMessages } from "@/lib/i18n/customUnits";
import type { Locale } from "@/lib/i18n/locale";
import { useCaptureMessages } from "@/lib/i18n/useCaptureMessages";
import { useLocale } from "@/lib/i18n/useLocale";
import type { RecipeResult, UnitCheck } from "@/lib/recipesClient";

import { NameChangeNotice } from "./NameChangeNotice";
import { RowControls } from "./RowControls";

type EditableIngredientLineProps = {
  line: LineView;
  index: number;
  count: number;
  errors: NonNullable<DraftErrors["lines"][number]>;
  /** The person's units. The line's current unit is added when it is not one of them. */
  units: string[];
  sizes: string[];
  /** Checks a word typed under "Other…"; without it the picker has no such entry (spec 055 R15). */
  onCheckUnit?: (word: string) => Promise<RecipeResult<UnitCheck>>;
  /** The notebook's catalog entries, for the match control (spec 018 FR-005). */
  catalog: string[];
  /** This line's name change, shown as a row above the card (spec 018 FR-003). */
  change?: NameChange;
  onUndoChange: (line: number) => void;
  onChange: (next: LineView) => void;
  onRemove: () => void;
  onMove: (direction: -1 | 1) => void;
  /** The language of the screen; the provider's language when not given. */
  locale?: Locale;
};

/** Borderless fields that read as text; a faint fill shows on hover and focus. */
const fieldClassName =
  "min-w-0 rounded-[0.4rem] border-0 bg-transparent px-1 py-[0.15rem] text-foreground outline-none hover:bg-background focus:bg-background disabled:opacity-40";

const headingClassName = "text-[1.05rem] font-semibold";

/** The picker value that swaps in the text field. Not a unit name. */
const OTHER_UNIT = "__other__";

const amountClassName = `${fieldClassName} ${headingClassName} shrink-0 text-accent`;

const labelClassName = "m-0 w-24 shrink-0 text-[0.8rem] font-medium text-muted";

/**
 * One ingredient line (spec 016 FR-007 to FR-012). The name and the amount (quantity, unit, and size
 * for the unit "unit") share the top line, then the catalog match and vague toggle. Below are
 * labelled preparation and note. The bottom bar holds remove and the move buttons. A vague amount
 * clears the quantity and the unit. Errors show under the row.
 */
function EditableIngredientLine({
  line,
  index,
  count,
  errors,
  units,
  sizes,
  onCheckUnit,
  catalog,
  change,
  onUndoChange,
  onChange,
  onRemove,
  onMove,
  locale,
}: EditableIngredientLineProps) {
  const t = useCaptureMessages(locale);
  const providerLocale = useLocale();
  const unitText = customUnitMessages[locale ?? providerLocale];
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

  const [typingUnit, setTypingUnit] = useState(false);
  const [typedUnit, setTypedUnit] = useState("");
  const [unitProblem, setUnitProblem] = useState<"notAUnit" | "checkFailed" | null>(null);
  const unitOptions =
    line.unit && !units.includes(line.unit) ? [...units, line.unit] : units;
  // The check is awaited, so it must apply to the line as it is by then.
  const latestLine = useRef(line);
  useEffect(() => {
    latestLine.current = line;
  }, [line]);

  /** A word typed under "Other…", checked when the field is left (spec 055 R15). */
  async function leaveTypedUnit() {
    const word = typedUnit.trim();
    if (!word || !onCheckUnit) {
      setTypingUnit(false);
      return;
    }
    const result = await onCheckUnit(word);
    if (!result.ok) {
      setUnitProblem("checkFailed");
      return;
    }
    if (result.value.outcome === "not_a_unit") {
      setUnitProblem("notAUnit");
      return;
    }
    const unit = result.value.unit;
    setUnitProblem(null);
    setTypedUnit("");
    setTypingUnit(false);
    onChange({
      ...latestLine.current,
      unit,
      size: unit === "unit" ? latestLine.current.size : null,
    });
  }

  return (
    <li className="flex min-w-0 flex-col gap-[var(--space-2)]">
      {change ? (
        <NameChangeNotice change={change} onUndo={onUndoChange} locale={locale} />
      ) : null}
      <Card>
        <div className="flex min-w-0 items-stretch">
          <div className="flex min-w-0 flex-1 flex-col">
            <CardHeader className="flex flex-col gap-1">
              <div className="flex items-center justify-between gap-2">
                <input
                  aria-label={t.ingredientName}
                  placeholder={t.ingredientName}
                  className={`${fieldClassName} ${headingClassName} flex-1`}
                  value={line.name}
                  onChange={(event) =>
                    onChange({ ...line, name: event.target.value })
                  }
                />
                <div className="flex shrink-0 items-center">
                  <input
                    type="number"
                    min="0"
                    step="any"
                    aria-label={t.quantity}
                    placeholder="0"
                    className={`${amountClassName} w-16 text-right [appearance:textfield] [&::-webkit-inner-spin-button]:appearance-none [&::-webkit-outer-spin-button]:appearance-none`}
                    value={line.quantity ?? ""}
                    disabled={line.vague}
                    onChange={(event) => {
                      setCachedAmount(null);
                      onChange({
                        ...line,
                        quantity:
                          event.target.value === ""
                            ? null
                            : Number(event.target.value),
                      });
                    }}
                  />
                  {typingUnit ? (
                    <input
                      aria-label={unitText.otherLabel}
                      autoFocus
                      maxLength={200}
                      className={`${amountClassName} w-24`}
                      value={typedUnit}
                      onChange={(event) => {
                        setUnitProblem(null);
                        setTypedUnit(event.target.value);
                      }}
                      onBlur={() => void leaveTypedUnit()}
                    />
                  ) : (
                  <SearchableSelect
                    aria-label={t.unit}
                    searchLabel={unitText.search}
                    noResults={unitText.noMatch}
                    className={amountClassName}
                    value={line.unit ?? ""}
                    disabled={line.vague}
                    options={[
                      { value: "", label: "—" },
                      ...unitOptions.map((unit) => ({ value: unit, label: unit })),
                      ...(onCheckUnit
                        ? [{ value: OTHER_UNIT, label: unitText.other, pinned: true }]
                        : []),
                    ]}
                    onChange={(value, query) => {
                      setCachedAmount(null);
                      if (value === OTHER_UNIT) {
                        // No unit until the word is checked, so Save can't go out without it.
                        setTypedUnit(query);
                        setTypingUnit(true);
                        onChange({ ...line, unit: null, size: null });
                        return;
                      }
                      onChange({
                        ...line,
                        unit: value === "" ? null : value,
                        size: value === "unit" ? line.size : null,
                      });
                    }}
                  />
                  )}
                  {sizeEnabled ? (
                    <select
                      aria-label={t.size}
                      className={amountClassName}
                      value={line.size ?? ""}
                      onChange={(event) => {
                        setCachedAmount(null);
                        onChange({
                          ...line,
                          size:
                            event.target.value === ""
                              ? null
                              : event.target.value,
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
                  aria-label={t.matchControl}
                  className={`${fieldClassName} text-[0.8rem] text-muted`}
                  value={matchedEntry ?? NEW_CHOICE}
                  onChange={(event) =>
                    onChange(chooseLineMatch(line, event.target.value))
                  }
                >
                  <option value={NEW_CHOICE}>
                    {t.newIngredient}
                  </option>
                  {catalog.map((entry) => (
                    <option key={entry} value={entry}>
                      {entry}
                    </option>
                  ))}
                </select>

                <label
                  htmlFor={vagueId}
                  className="flex shrink-0 items-center gap-2 text-[0.8rem] text-muted"
                >
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
                  {t.vague}
                </label>
              </div>
            </CardHeader>

            <CardBody>
              <div className="flex items-center gap-2">
                <h3 className={labelClassName}>
                  <label htmlFor={preparationId}>
                    {t.preparation}:
                  </label>
                </h3>
                <input
                  id={preparationId}
                  className={`${fieldClassName} flex-1 text-[0.9rem]`}
                  value={line.preparation ?? ""}
                  onChange={(event) =>
                    onChange({
                      ...line,
                      preparation: event.target.value || null,
                    })
                  }
                />
              </div>

              <div className="flex items-center gap-2">
                <h3 className={labelClassName}>
                  <label htmlFor={noteId}>{t.note}:</label>
                </h3>
                <input
                  id={noteId}
                  className={`${fieldClassName} flex-1 text-[0.9rem]`}
                  value={line.note ?? ""}
                  onChange={(event) =>
                    onChange({ ...line, note: event.target.value || null })
                  }
                />
              </div>

              {errors.map((code) => (
                <p
                  key={code}
                  role="alert"
                  className="m-0 text-[0.8rem] text-error"
                >
                  {t.errors[code]}
                </p>
              ))}
              {unitProblem ? (
                <p role="alert" className="m-0 text-[0.8rem] text-error">
                  {unitText[unitProblem]}
                </p>
              ) : null}
            </CardBody>
          </div>
          <RowControls
            className="px-2 py-3"
            index={index}
            count={count}
            onRemove={onRemove}
            onMove={onMove}
            locale={locale}
          />
        </div>
      </Card>
    </li>
  );
}

/** What the read-only card needs of a line; a stored recipe's line has all of it. */
export type ReadOnlyLine = Pick<
  LineView,
  "name" | "vague" | "quantity" | "unit" | "size" | "preparation" | "note"
>;

type ReadOnlyIngredientLineProps = {
  line: ReadOnlyLine;
  /** Marks the card as display only: no fields, no match control, no row controls. */
  readOnly: true;
  locale?: Locale;
};

/** The amount as one piece of text: "1 cup", "2 large", or nothing for a vague amount. */
function amountText(line: ReadOnlyLine): string {
  if (line.vague || line.quantity === null) return "";
  const unit = line.unit === "unit" ? line.size : line.unit;
  return [formatQuantity(line.quantity), unit].filter(Boolean).join(" ");
}

/**
 * The same card as the editable row, with the fields shown as text (spec 027): the name and the
 * amount share the top line; the preparation and the note follow only when the line has them.
 */
function ReadOnlyIngredientLine({ line, locale }: { line: ReadOnlyLine; locale?: Locale }) {
  const t = useCaptureMessages(locale);
  const amount = amountText(line);
  return (
    <li className="flex min-w-0 flex-col gap-[var(--space-2)]">
      <Card>
        <CardHeader className="flex items-center justify-between gap-2">
          <span className={`${headingClassName} min-w-0 flex-1 px-1 text-foreground`}>
            {line.name}
          </span>
          {amount ? (
            <span className={`${headingClassName} shrink-0 px-1 text-accent`}>{amount}</span>
          ) : null}
        </CardHeader>
        {line.preparation || line.note ? (
          <CardBody>
            {line.preparation ? (
              <div className="flex items-center gap-2">
                <h3 className={labelClassName}>{t.preparation}:</h3>
                <span className="flex-1 px-1 text-[0.9rem] text-foreground">
                  {line.preparation}
                </span>
              </div>
            ) : null}
            {line.note ? (
              <div className="flex items-center gap-2">
                <h3 className={labelClassName}>{t.note}:</h3>
                <span className="flex-1 px-1 text-[0.9rem] text-foreground">{line.note}</span>
              </div>
            ) : null}
          </CardBody>
        ) : null}
      </Card>
    </li>
  );
}

export type IngredientLineRowProps =
  | (EditableIngredientLineProps & { readOnly?: false })
  | ReadOnlyIngredientLineProps;

/** One ingredient line, to edit at capture and in an edit, or display only on the detail. */
export function IngredientLineRow(props: IngredientLineRowProps) {
  if (props.readOnly) return <ReadOnlyIngredientLine line={props.line} locale={props.locale} />;
  return <EditableIngredientLine {...props} />;
}
