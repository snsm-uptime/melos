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

/** The notebook invite link page — EN/ES (spec 057). */
export const notebookInviteMessages = {
  en: {
    title: "Join a notebook",
    accepting: "Joining the notebook…",
    loading: "Opening your invite…",
    previewInvited: (alias: string, name: string) =>
      `${alias} invited you to the notebook “${name}”.`,
    previewNotebook: (name: string) => `You're invited to the notebook “${name}”.`,
    previewEmail: (hint: string) => `This invite was sent to ${hint}. Use that email.`,
    signInCta: "Sign in to join",
    createAccountCta: "Create an account",
    reopenNote:
      "If you create an account, open this link again from your email once it's ready.",
    verifyCta: "Verify email to continue",
    errorExpired:
      "This invite link is invalid or has expired. Ask the notebook owner for a new invite.",
    errorMismatch: "This invite is for another email. Sign in with the email it was sent to.",
    errorNotVerified: "Verify your email before joining this notebook.",
    errorGeneric: "Something went wrong. Try again.",
  },
  es: {
    title: "Unirse a un cuaderno",
    accepting: "Uniéndote al cuaderno…",
    loading: "Abriendo tu invitación…",
    previewInvited: (alias: string, name: string) =>
      `${alias} te invitó al cuaderno «${name}».`,
    previewNotebook: (name: string) => `Te invitaron al cuaderno «${name}».`,
    previewEmail: (hint: string) => `Esta invitación se envió a ${hint}. Usa ese correo.`,
    signInCta: "Iniciar sesión para unirme",
    createAccountCta: "Crear una cuenta",
    reopenNote: "Si creas una cuenta, abre este enlace otra vez desde tu correo cuando la tengas.",
    verifyCta: "Verificar correo para continuar",
    errorExpired:
      "Este enlace de invitación no es válido o ha caducado. Pide uno nuevo al dueño del cuaderno.",
    errorMismatch: "Esta invitación es para otro correo. Inicia sesión con el correo al que se envió.",
    errorNotVerified: "Verifica tu correo antes de unirte a este cuaderno.",
    errorGeneric: "Algo salió mal. Inténtalo de nuevo.",
  },
} as const;

export type InviteMessageKey = keyof (typeof inviteMessages)["en"];
export type { Locale } from "@/lib/i18n/locale";
