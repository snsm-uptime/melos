"use client";

import { StarIcon } from "@/app/icons";
import { IconButton } from "@/components/IconButton";
import { Tooltip } from "@/components/Tooltip";
import { usePanelLayout } from "./panelLayout";

/** The end of a kitchen row: a filled star on the default, otherwise a button to choose it. */
export function KitchenStar({
  isDefault,
  defaultLabel,
  setLabel,
  onSet,
}: {
  isDefault: boolean;
  defaultLabel: string;
  setLabel: string;
  onSet: () => void;
}) {
  const { openOnlyClass } = usePanelLayout();
  if (isDefault) {
    return (
      <span
        className={`absolute inset-y-0 right-0 inline-flex size-11 items-center justify-center text-accent ${openOnlyClass}`}
      >
        <Tooltip label={defaultLabel}>
          <span role="img" aria-label={defaultLabel}>
            <StarIcon filled className="size-5" />
          </span>
        </Tooltip>
      </span>
    );
  }
  return (
    <span className={`absolute inset-y-0 right-0 ${openOnlyClass}`}>
      <IconButton
        type="button"
        variant="ghost"
        className="size-11"
        label={setLabel}
        icon={<StarIcon className="size-5" />}
        onClick={onSet}
      />
    </span>
  );
}
