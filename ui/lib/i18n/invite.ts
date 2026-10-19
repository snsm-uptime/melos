/** Invitee accept / signup chrome — EN/ES (Story 2.4). */

export const inviteMessages = {
  en: {
    acceptTitle: "Join kitchen",
    acceptSubtitle: "Accept this invitation to open the shared kitchen.",
    accepting: "Joining the kitchen…",
    acceptSuccess: "Joined. Opening the kitchen…",
    signInPrompt: "Sign in with the email this invite was sent to, then you’ll join the kitchen.",
    signInCta: "Sign in to join",
    verifyCta: "Verify email to continue",
    errorExpired:
      "This invite link is invalid or has expired. Ask the kitchen owner for a new invite.",
    errorMismatch: "Use the email address this invite was sent to.",
    errorNotVerified: "Verify your email before joining this kitchen.",
    errorUnauthorized: "Sign in to accept this invite.",
    errorGeneric: "Something went wrong. Try again.",
    inviteSignupSubtitle: "Create your account to join “{kitchenName}”.",
    emailMatchHint: "Use the email this invite was sent to ({emailHint}).",
  },
  es: {
    acceptTitle: "Unirse a la cocina",
    acceptSubtitle: "Acepta esta invitación para abrir la cocina compartida.",
    accepting: "Uniéndote a la cocina…",
    acceptSuccess: "Listo. Abriendo la cocina…",
    signInPrompt:
      "Inicia sesión con el correo de esta invitación y te unirás a la cocina.",
    signInCta: "Iniciar sesión para unirme",
    verifyCta: "Verificar correo para continuar",
    errorExpired:
      "Este enlace de invitación no es válido o ha caducado. Pide uno nuevo al dueño de la cocina.",
    errorMismatch: "Usa el correo al que se envió esta invitación.",
    errorNotVerified: "Verifica tu correo antes de unirte a esta cocina.",
    errorUnauthorized: "Inicia sesión para aceptar esta invitación.",
    errorGeneric: "Algo salió mal. Inténtalo de nuevo.",
    inviteSignupSubtitle: "Crea tu cuenta para unirte a «{kitchenName}».",
    emailMatchHint: "Usa el correo al que se envió esta invitación ({emailHint}).",
  },
} as const;

export type InviteMessageKey = keyof (typeof inviteMessages)["en"];
export type { Locale } from "@/lib/i18n/locale";
