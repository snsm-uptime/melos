"use client";

import {
  useEffect,
  useId,
  useRef,
  useState,
  type CSSProperties,
  type KeyboardEvent,
} from "react";
import { createPortal } from "react-dom";

import { BackIcon } from "@/app/icons";
import { menuSurface } from "@/components/MenuSurface";

export type SearchableSelectOption = {
  value: string;
  label: string;
  /** Stays in the list whatever is typed, such as an "Other…" entry. */
  pinned?: boolean;
};

export type SearchableSelectProps = {
  value: string;
  options: SearchableSelectOption[];
  disabled?: boolean;
  /** Replaces the trigger's look, so it can read as part of the row around it. */
  className?: string;
  /** Width of the open panel in px. Long option labels need a wider panel. */
  panelWidth?: number;
  "aria-label": string;
  /** Label and placeholder of the search field. */
  searchLabel: string;
  /** Shown when the search finds no option. */
  noResults: string;
  /** `query` is what was typed, for a pinned option that wants to carry it on. */
  onChange: (value: string, query: string) => void;
};

const DEFAULT_PANEL_WIDTH_PX = 176;
/** The search field plus the list at its tallest (`max-h-56`). */
const PANEL_HEIGHT_PX = 288;
const EDGE_GAP_PX = 8;
const TRIGGER_GAP_PX = 4;

/** Lower case, no accents: "cucharón" is found by typing "cucharon". */
function searchable(text: string): string {
  return text
    .normalize("NFD")
    .replace(/\p{M}/gu, "")
    .toLowerCase()
    .trim();
}

/** Right-aligned to the trigger, opening upward when there is no room below. */
function panelPosition(trigger: HTMLElement, panelWidth: number): CSSProperties {
  const rect = trigger.getBoundingClientRect();
  const left = Math.max(
    EDGE_GAP_PX,
    Math.min(
      rect.right - panelWidth,
      window.innerWidth - panelWidth - EDGE_GAP_PX,
    ),
  );
  const below = window.innerHeight - rect.bottom;
  return below < PANEL_HEIGHT_PX && rect.top > below
    ? { left, bottom: window.innerHeight - rect.top + TRIGGER_GAP_PX }
    : { left, top: rect.bottom + TRIGGER_GAP_PX };
}

/**
 * A select with a search field. The panel is portalled and fixed so that a card's
 * `overflow-hidden` can't clip it. Focus stays in the field while the list is walked.
 */
export function SearchableSelect({
  value,
  options,
  disabled = false,
  className,
  panelWidth = DEFAULT_PANEL_WIDTH_PX,
  "aria-label": ariaLabel,
  searchLabel,
  noResults,
  onChange,
}: SearchableSelectProps) {
  const listboxId = `${useId()}-listbox`;
  const triggerRef = useRef<HTMLButtonElement>(null);
  const panelRef = useRef<HTMLDivElement>(null);
  const listRef = useRef<HTMLUListElement>(null);
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [highlight, setHighlight] = useState(0);
  const [position, setPosition] = useState<CSSProperties>({});

  const needle = searchable(query);
  const visible = options.filter(
    (option) => option.pinned || searchable(option.label).includes(needle),
  );
  const nothingFound = needle !== "" && visible.every((option) => option.pinned);

  function show() {
    if (disabled || !triggerRef.current) return;
    setQuery("");
    setHighlight(
      Math.max(
        0,
        options.findIndex((option) => option.value === value),
      ),
    );
    setPosition(panelPosition(triggerRef.current, panelWidth));
    setOpen(true);
  }

  function hide() {
    setOpen(false);
  }

  function choose(option: SearchableSelectOption) {
    hide();
    triggerRef.current?.focus();
    onChange(option.value, query.trim());
  }

  useEffect(() => {
    if (!open) return;
    function follow() {
      if (triggerRef.current) setPosition(panelPosition(triggerRef.current, panelWidth));
    }
    function onPointerDown(event: PointerEvent) {
      const target = event.target as Node;
      if (panelRef.current?.contains(target)) return;
      if (triggerRef.current?.contains(target)) return;
      setOpen(false);
    }
    window.addEventListener("scroll", follow, true);
    window.addEventListener("resize", follow);
    document.addEventListener("pointerdown", onPointerDown);
    return () => {
      window.removeEventListener("scroll", follow, true);
      window.removeEventListener("resize", follow);
      document.removeEventListener("pointerdown", onPointerDown);
    };
  }, [open, panelWidth]);

  useEffect(() => {
    if (!open) return;
    listRef.current
      ?.querySelector('[data-highlighted="true"]')
      ?.scrollIntoView?.({ block: "nearest" });
  }, [open, highlight, query]);

  function onTriggerKeyDown(event: KeyboardEvent<HTMLButtonElement>) {
    if (event.key === "ArrowDown" || event.key === "ArrowUp") {
      event.preventDefault();
      show();
    }
  }

  function onSearchKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === "Escape") {
      event.preventDefault();
      hide();
      triggerRef.current?.focus();
    } else if (event.key === "ArrowDown") {
      event.preventDefault();
      setHighlight(Math.min(visible.length - 1, highlight + 1));
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      setHighlight(Math.max(0, highlight - 1));
    } else if (event.key === "Enter") {
      event.preventDefault();
      const option = visible[highlight];
      if (option) choose(option);
    }
  }

  return (
    <>
      <button
        type="button"
        role="combobox"
        ref={triggerRef}
        className={`inline-flex items-center gap-1 ${className ?? ""}`}
        disabled={disabled}
        aria-label={ariaLabel}
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-controls={open ? listboxId : undefined}
        // Keeps the search field's blur from closing the panel just before the click toggles it.
        onMouseDown={(event) => {
          if (open) event.preventDefault();
        }}
        onClick={() => (open ? hide() : show())}
        onKeyDown={onTriggerKeyDown}
      >
        <span className="whitespace-nowrap">
          {options.find((option) => option.value === value)?.label ?? ""}
        </span>
        <BackIcon
          className={`size-[0.8em] shrink-0 opacity-60 transition-transform duration-200 ease-out motion-reduce:transition-none ${open ? "rotate-90" : "-rotate-90"}`}
        />
      </button>
      {open
        ? createPortal(
            <div
              ref={panelRef}
              className={`${menuSurface.panel} fixed z-50 p-1`}
              style={{ ...position, width: panelWidth }}
            >
              <input
                type="text"
                role="combobox"
                autoFocus
                autoComplete="off"
                aria-label={searchLabel}
                aria-expanded="true"
                aria-controls={listboxId}
                aria-autocomplete="list"
                aria-activedescendant={
                  visible.length > 0 ? `${listboxId}-opt-${highlight}` : undefined
                }
                placeholder={searchLabel}
                // 1rem: a smaller field makes iOS zoom the page when it takes focus.
                className="mb-1 box-border w-full rounded-[var(--rounded-sm)] border border-border bg-background px-2 py-1 text-[1rem] text-foreground outline-none"
                value={query}
                onChange={(event) => {
                  setQuery(event.target.value);
                  setHighlight(0);
                }}
                onBlur={hide}
                onKeyDown={onSearchKeyDown}
              />
              {nothingFound ? (
                <p className="m-0 px-2 py-1 text-[0.85rem] text-muted">{noResults}</p>
              ) : null}
              <ul
                id={listboxId}
                ref={listRef}
                role="listbox"
                aria-label={ariaLabel}
                className="m-0 max-h-56 list-none overflow-y-auto p-0"
                // The field keeps focus, also when the list's scrollbar is dragged.
                onMouseDown={(event) => event.preventDefault()}
              >
                {visible.map((option, index) => {
                  const highlighted = index === highlight;
                  return (
                    <li
                      key={option.value}
                      id={`${listboxId}-opt-${index}`}
                      role="option"
                      aria-selected={option.value === value}
                      data-highlighted={highlighted}
                      className={menuSurface.item}
                      style={
                        highlighted && option.value !== value
                          ? { background: "var(--menu-item-hover)" }
                          : undefined
                      }
                      onClick={() => choose(option)}
                    >
                      {option.label}
                    </li>
                  );
                })}
              </ul>
            </div>,
            document.body,
          )
        : null}
    </>
  );
}
