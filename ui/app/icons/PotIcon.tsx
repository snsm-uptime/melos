/** The default image until a recipe has its own: a cooking pot. */
export function PotIcon() {
  return (
    <svg
      viewBox="0 0 24 24"
      width="28"
      height="28"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      data-testid="recipe-pot-icon"
    >
      <path d="M4 10h16v6a4 4 0 0 1-4 4H8a4 4 0 0 1-4-4v-6Z" />
      <path d="M2 10h2M20 10h2" />
      <path d="M9 7c0-1.2 1-1.2 1-2.4M14 7c0-1.2 1-1.2 1-2.4" />
    </svg>
  );
}
