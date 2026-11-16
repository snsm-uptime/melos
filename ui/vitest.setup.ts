import { beforeEach } from "vitest";

/** React 19 `act()` reads this global; jsdom does not set it on its own. */
function markReactActEnvironment() {
  Object.defineProperty(globalThis, "IS_REACT_ACT_ENVIRONMENT", {
    configurable: true,
    writable: true,
    value: true,
  });
}

markReactActEnvironment();
beforeEach(markReactActEnvironment);

/** jsdom has no layout, so nothing ever resizes; a test that needs it stubs its own. */
globalThis.ResizeObserver ??= class {
  observe() {}
  unobserve() {}
  disconnect() {}
};

/** Capture text kept in session storage (spec 076) must not leak from one test to the next. */
beforeEach(() => {
  if (typeof window !== "undefined") window.sessionStorage.clear();
});
