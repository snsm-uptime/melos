import { pickAvatarColor, pickTextColor } from "@/lib/avatarColor";

/** A kitchen's first letter on a rounded square; the colour separates same-letter kitchens. */
export function KitchenIcon({ id, name }: { id: string; name: string }) {
  const background = pickAvatarColor(id);
  return (
    <span
      aria-hidden="true"
      className="inline-flex size-7 shrink-0 items-center justify-center rounded-[8px] text-[0.8rem] font-[600] leading-none"
      style={{ backgroundColor: background, color: pickTextColor(background) }}
    >
      {name.trim().charAt(0).toUpperCase() || "?"}
    </span>
  );
}
