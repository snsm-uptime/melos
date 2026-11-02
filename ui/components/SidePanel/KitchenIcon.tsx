import { Badge } from "@/components/Badge";
import { pickAvatarColor, pickTextColor } from "@/lib/avatarColor";

/** A kitchen's first letter on a rounded square; the colour separates same-letter kitchens. */
export function KitchenIcon({
  id,
  name,
  current = false,
}: {
  id: string;
  name: string;
  /** Pins the badge that marks the kitchen you are in; it shows on the closed panel too. */
  current?: boolean;
}) {
  const background = pickAvatarColor(id);
  return (
    <span
      aria-hidden="true"
      className="relative inline-flex size-7 shrink-0 items-center justify-center rounded-[8px] text-[0.8rem] font-[600] leading-none"
      style={{ backgroundColor: background, color: pickTextColor(background) }}
    >
      {name.trim().charAt(0).toUpperCase() || "?"}
      {current ? (
        <Badge size="sm" className="absolute -bottom-1 -right-1.5 ring-2 ring-surface" />
      ) : null}
    </span>
  );
}
