"use client";

import { useEffect, useRef, type ReactNode } from "react";

import { ArrowIcon } from "@/app/icons";

import styles from "./Tabs.module.scss";

/** The app's tab switch: a `tablist` of underlined tabs, each with an icon and a label. */
export function TabList({
  label,
  children,
  cycle,
}: {
  label: string;
  children: ReactNode;
  /** One row that never wraps: arrows on each side select the previous or next tab, wrapping around. */
  cycle?: { previousLabel: string; nextLabel: string };
}) {
  const list = useRef<HTMLDivElement>(null);

  // Keeps the selected tab in view, whether chosen by an arrow or a click.
  useEffect(() => {
    if (!cycle) return;
    list.current
      ?.querySelector<HTMLElement>('[role="tab"][aria-selected="true"]')
      ?.scrollIntoView?.({
        block: "nearest",
        inline: "nearest",
        behavior: "smooth",
      });
  });

  function step(by: number) {
    const tabs = Array.from(
      list.current?.querySelectorAll<HTMLButtonElement>('[role="tab"]') ?? [],
    );
    if (tabs.length === 0) return;
    const current = tabs.findIndex(
      (tab) => tab.getAttribute("aria-selected") === "true",
    );
    const next = tabs[(current + by + tabs.length) % tabs.length];
    next.click();
    next.focus();
  }

  const tablist = (
    <div
      ref={list}
      role="tablist"
      aria-label={label}
      className={cycle ? `${styles.tabs} ${styles.tabsCycle}` : styles.tabs}
    >
      {children}
    </div>
  );
  if (!cycle) return tablist;
  return (
    <div className={styles.cycle}>
      <button
        type="button"
        className={styles.arrow}
        aria-label={cycle.previousLabel}
        onClick={() => step(-1)}
      >
        <ArrowIcon className="size-5" />
      </button>
      {tablist}
      <button
        type="button"
        className={styles.arrow}
        aria-label={cycle.nextLabel}
        onClick={() => step(1)}
      >
        <ArrowIcon className="size-5 rotate-180" />
      </button>
    </div>
  );
}

export function TabButton({
  id,
  selected,
  onSelect,
  icon,
  label,
}: {
  id: string;
  selected: boolean;
  onSelect: () => void;
  icon: ReactNode;
  label: string;
}) {
  return (
    <button
      type="button"
      role="tab"
      id={id}
      aria-selected={selected}
      className={selected ? `${styles.tab} ${styles.tabActive}` : styles.tab}
      onClick={onSelect}
    >
      {icon}
      <span>{label}</span>
    </button>
  );
}
