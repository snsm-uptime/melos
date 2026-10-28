import type { Metadata } from "next";
import { Manrope, Petrona } from "next/font/google";

import { AppShell } from "@/components/AppShell";
import {
  PreferencesProvider,
  themeBootScript,
} from "@/components/PreferencesProvider";

import { getServerLocale } from "@/lib/serverLocale";

import "./globals.css";

const manrope = Manrope({
  subsets: ["latin"],
  variable: "--font-ui",
  display: "swap",
});

const petrona = Petrona({
  subsets: ["latin"],
  variable: "--font-brand",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Melos",
  description: "Menus Everyone Loves to Share — a shared home cookbook",
};

export default async function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  // One language source for the page: the account's saved language, the signed-out pick, or
  // Spanish (spec 063). The provider starts from the same value, so nothing flips.
  const locale = await getServerLocale();
  return (
    <html
      lang={locale}
      className={`${manrope.variable} ${petrona.variable}`}
      suppressHydrationWarning
    >
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeBootScript }} />
      </head>
      <body>
        <PreferencesProvider initialLocale={locale}>
          <AppShell>{children}</AppShell>
        </PreferencesProvider>
      </body>
    </html>
  );
}
