import { forwardRef } from "react";

import { BaseButton, type BaseButtonProps, type DistributiveOmit } from "./BaseButton";

type PrimaryButtonProps = DistributiveOmit<BaseButtonProps, "variant">;

/** Violet filled CTA (spec 072) — outline idle, fills solid on hover. rounded-sm only; never pill. */
export const PrimaryButton = forwardRef<
  HTMLButtonElement | HTMLAnchorElement,
  PrimaryButtonProps
>(function PrimaryButton(props, ref) {
  return <BaseButton variant="primary" ref={ref} {...props} />;
});
