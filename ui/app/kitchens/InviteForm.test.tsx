/** @vitest-environment jsdom */

import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { InviteForm } from "./InviteForm";
import { kitchensMessages } from "@/lib/i18n/kitchens";

vi.mock("./kitchens.module.scss", () => ({
  default: new Proxy(
    {},
    {
      get: (_t, prop) => String(prop),
    },
  ),
}));

vi.mock("@/components/FormIconSubmit/FormIconSubmit.module.scss", () => ({
  default: new Proxy(
    {},
    {
      get: (_t, prop) => String(prop),
    },
  ),
}));

const inviteMember = vi.fn();

vi.mock("./kitchensClient", async () => {
  const actual = await vi.importActual<typeof import("./kitchensClient")>("./kitchensClient");
  return {
    ...actual,
    inviteMember: (...args: unknown[]) => inviteMember(...args),
  };
});

const messages = {
  inviteTitle: kitchensMessages.en.inviteTitle,
  inviteLabel: kitchensMessages.en.inviteLabel,
  inviteSubmit: kitchensMessages.en.inviteSubmit,
  inviteSending: kitchensMessages.en.inviteSending,
  inviteSent: kitchensMessages.en.inviteSent,
  errorGeneric: kitchensMessages.en.errorGeneric,
  errorInvalidName: kitchensMessages.en.errorInvalidName,
  errorInvalidEmail: kitchensMessages.en.errorInvalidEmail,
  errorForbidden: kitchensMessages.en.errorInviteForbidden,
  errorUnauthorized: kitchensMessages.en.errorUnauthorized,
  errorAlreadyMember: kitchensMessages.en.errorAlreadyMember,
  errorSmtp: kitchensMessages.en.errorSmtp,
};

async function setEmailAndSubmit(container: HTMLElement, email: string) {
  const input = container.querySelector('input[name="email"]') as HTMLInputElement;
  const form = container.querySelector("form") as HTMLFormElement;
  await act(async () => {
    const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value")?.set;
    setter?.call(input, email);
    input.dispatchEvent(new Event("input", { bubbles: true }));
    input.dispatchEvent(new Event("change", { bubbles: true }));
  });
  await act(async () => {
    form.requestSubmit();
  });
}

describe("InviteForm", () => {
  let container: HTMLDivElement;
  let root: Root;

  beforeEach(() => {
    inviteMember.mockReset();
    container = document.createElement("div");
    document.body.appendChild(container);
    root = createRoot(container);
  });

  afterEach(() => {
    act(() => {
      root.unmount();
    });
    container.remove();
  });

  it("send control stays disabled until an email is entered", async () => {
    await act(async () => {
      root.render(<InviteForm kitchenId="kitchen-1" messages={messages} />);
    });

    const button = container.querySelector('button[type="submit"]') as HTMLButtonElement;
    expect(button).not.toBeNull();
    expect(button.getAttribute("aria-label")).toBe(messages.inviteSubmit);
    expect(button.disabled).toBe(true);

    const input = container.querySelector('input[name="email"]') as HTMLInputElement;
    await act(async () => {
      const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value")?.set;
      setter?.call(input, "peer@example.com");
      input.dispatchEvent(new Event("input", { bubbles: true }));
      input.dispatchEvent(new Event("change", { bubbles: true }));
    });

    expect(button.disabled).toBe(false);
  });

  it("shows invite-sent confirmation on success", async () => {
    inviteMember.mockResolvedValue({
      ok: true,
      invite: { status: "sent", template_kind: "join", invite_id: "inv-1" },
    });

    await act(async () => {
      root.render(<InviteForm kitchenId="kitchen-1" messages={messages} />);
    });

    await setEmailAndSubmit(container, "peer@example.com");

    expect(inviteMember).toHaveBeenCalledWith("kitchen-1", "peer@example.com", messages);
    expect(container.querySelector('[role="status"]')?.textContent).toBe(
      kitchensMessages.en.inviteSent,
    );
    expect(container.querySelector('[role="alert"]')).toBeNull();
  });

  it("does not keep the reserved error slot when the sent message is showing", async () => {
    inviteMember.mockResolvedValue({
      ok: true,
      invite: { status: "sent", template_kind: "join", invite_id: "inv-1" },
    });

    await act(async () => {
      root.render(<InviteForm kitchenId="kitchen-1" messages={messages} reserveErrorHeight />);
    });

    await setEmailAndSubmit(container, "peer@example.com");

    expect(container.querySelector('[role="status"]')?.textContent).toBe(
      kitchensMessages.en.inviteSent,
    );
    expect(container.querySelector(".inviteErrorSlot")).toBeNull();
    expect(container.querySelector('[role="alert"]')).toBeNull();
  });

  it("shows error and does not claim sent on SMTP failure", async () => {
    inviteMember.mockResolvedValue({
      ok: false,
      error: kitchensMessages.en.errorSmtp,
    });

    await act(async () => {
      root.render(<InviteForm kitchenId="kitchen-1" messages={messages} />);
    });

    await setEmailAndSubmit(container, "peer@example.com");

    expect(container.querySelector('[role="alert"]')?.textContent).toBe(
      kitchensMessages.en.errorSmtp,
    );
    expect(container.querySelector('[role="status"]')).toBeNull();
  });

  it("clears error when the email input changes", async () => {
    inviteMember.mockResolvedValue({
      ok: false,
      error: kitchensMessages.en.errorSmtp,
    });

    await act(async () => {
      root.render(<InviteForm kitchenId="kitchen-1" messages={messages} />);
    });

    await setEmailAndSubmit(container, "peer@example.com");
    expect(container.querySelector('[role="alert"]')).not.toBeNull();

    const input = container.querySelector('input[name="email"]') as HTMLInputElement;
    await act(async () => {
      const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value")?.set;
      setter?.call(input, "other@example.com");
      input.dispatchEvent(new Event("input", { bubbles: true }));
      input.dispatchEvent(new Event("change", { bubbles: true }));
    });

    expect(container.querySelector('[role="alert"]')).toBeNull();
  });
});
