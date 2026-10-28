/** @vitest-environment jsdom */

import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { readLanguagePick, writeLanguagePick, clearLanguagePick } from "@/lib/i18n/languagePick";

const attempt = vi.hoisted(() => vi.fn());
vi.mock("./signInClient", () => ({ attemptSignIn: attempt }));
vi.mock("@/app/kitchens/membershipKitchensStore", () => ({ resetMembershipKitchensStore: vi.fn() }));

import { SignInForm } from "./SignInForm";

function setValue(element: HTMLInputElement, value: string) {
  Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value")?.set?.call(element, value);
  element.dispatchEvent(new Event("input", { bubbles: true }));
}

describe("SignInForm and the signed-out language pick (spec 063)", () => {
  let container: HTMLDivElement;
  let root: Root;
  const assign = vi.fn();
  const originalLocation = window.location;

  beforeEach(() => {
    container = document.createElement("div");
    document.body.appendChild(container);
    root = createRoot(container);
    attempt.mockReset();
    assign.mockReset();
    Object.defineProperty(window, "location", {
      configurable: true,
      value: { ...originalLocation, assign },
    });
    writeLanguagePick("en");
  });

  afterEach(() => {
    act(() => root.unmount());
    container.remove();
    Object.defineProperty(window, "location", { configurable: true, value: originalLocation });
    clearLanguagePick();
  });

  async function submit() {
    act(() => root.render(<SignInForm locale="es" returnTo="/home" />));
    act(() => setValue(container.querySelector("#email") as HTMLInputElement, "a@example.com"));
    act(() => setValue(container.querySelector("#password") as HTMLInputElement, "password1"));
    await act(async () => {
      container.querySelector("form")?.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
    });
  }

  it("drops the pick made while signed out when the sign-in succeeds", async () => {
    attempt.mockResolvedValue({ ok: true, returnTo: "/home" });
    await submit();
    expect(readLanguagePick()).toBeNull();
    expect(assign).toHaveBeenCalledWith("/home");
  });

  it("keeps the pick when the sign-in fails", async () => {
    attempt.mockResolvedValue({ ok: false, error: "Correo o contraseña incorrectos." });
    await submit();
    expect(readLanguagePick()).toBe("en");
    expect(assign).not.toHaveBeenCalled();
    expect(container.textContent).toContain("Correo o contraseña incorrectos.");
  });
});
