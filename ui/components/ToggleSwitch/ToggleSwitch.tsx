"use client";

type ToggleSwitchProps = {
  checked: boolean;
  onChange: (next: boolean) => void;
  disabled?: boolean;
  /** The accessible name of the switch. */
  label: string;
};

const TRACK_W = 44;
const TRACK_H = 24;
const BORDER = 2;
const KNOB = 16;

/**
 * A two-state switch, as in the owner's mockup.
 * Off: an accent outline track with a solid accent knob on the left.
 * On: a filled orange (accent-fill) track with a knob in the surface colour on the right, so it
 * reads as a hole.
 * The track is a flex row, so the knob is centred vertically and sits on the chosen side.
 */
export function ToggleSwitch({ checked, onChange, disabled, label }: ToggleSwitchProps) {
  const accent = checked ? "var(--accent-fill)" : "var(--accent)";
  return (
    <button
      type="button"
      role="switch"
      aria-label={label}
      aria-checked={checked}
      disabled={disabled}
      onClick={() => onChange(!checked)}
      style={{
        boxSizing: "border-box",
        display: "flex",
        alignItems: "center",
        justifyContent: checked ? "flex-end" : "flex-start",
        flexShrink: 0,
        width: TRACK_W,
        height: TRACK_H,
        padding: (TRACK_H - KNOB) / 2 - BORDER,
        borderRadius: TRACK_H,
        border: `${BORDER}px solid ${accent}`,
        background: checked ? "var(--accent-fill)" : "transparent",
        cursor: disabled ? "not-allowed" : "pointer",
        opacity: disabled ? 0.5 : 1,
        transition: "background 150ms ease, border-color 150ms ease",
      }}
    >
      <span
        aria-hidden="true"
        style={{
          display: "block",
          width: KNOB,
          height: KNOB,
          borderRadius: "50%",
          background: checked ? "var(--surface)" : "var(--accent)",
          transition: "background 150ms ease",
        }}
      />
    </button>
  );
}
