/** The shortest time a first load shows the loader, so a page has room to settle. */
export const MIN_LOADING_MS = 500;

/** The work's result, no sooner than `ms` from now. A failure also waits, so the loader holds. */
export async function withMinimumLoading<T>(
  work: Promise<T>,
  ms: number = MIN_LOADING_MS,
): Promise<T> {
  const minimum = new Promise<void>((resolve) => setTimeout(resolve, ms));
  const [result] = await Promise.allSettled([work, minimum]);
  if (result.status === "rejected") throw result.reason;
  return result.value;
}
