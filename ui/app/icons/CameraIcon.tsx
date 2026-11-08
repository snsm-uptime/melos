import type { SVGProps } from "react";

/** A filled camera: a body with a top bump and a round lens cut out (even-odd). */
export function CameraIcon({ className, ...props }: SVGProps<SVGSVGElement>) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="currentColor"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
      {...props}
    >
      <path
        fillRule="evenodd"
        d="M8.2 4.5h7.6l1.8 2H20a2.5 2.5 0 0 1 2.5 2.5v9A2.5 2.5 0 0 1 20 20.5H4A2.5 2.5 0 0 1 1.5 18V9A2.5 2.5 0 0 1 4 6.5h2.4l1.8-2ZM12 9a4 4 0 1 0 0 8 4 4 0 0 0 0-8Z"
      />
    </svg>
  );
}
