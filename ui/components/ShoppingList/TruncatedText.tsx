"use client";

import { useLayoutEffect, useRef, useState } from "react";

import { Tooltip } from "@/components/Tooltip";

/**
 * One line of text cut with an ellipsis when it doesn't fit, with the whole text in a tooltip
 * only while it is cut. Re-measured whenever its box resizes (a column change) or the text changes.
 */
export function TruncatedText({ text, className }: { text: string; className?: string }) {
  const ref = useRef<HTMLSpanElement>(null);
  const [cut, setCut] = useState(false);

  useLayoutEffect(() => {
    const node = ref.current;
    if (!node) return;
    const measure = () => setCut(node.scrollWidth > node.clientWidth);
    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(node);
    return () => observer.disconnect();
  }, [text]);

  return (
    <Tooltip label={text} disabled={!cut}>
      <span ref={ref} className={`min-w-0 truncate ${className ?? ""}`}>
        {text}
      </span>
    </Tooltip>
  );
}
