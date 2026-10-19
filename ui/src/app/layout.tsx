import type { Metadata } from "next";
import "../styles/globals.css";

export const metadata: Metadata = {
  title: "Melos - Recipe & Kitchen System",
  description: "Capture, organize, and share recipes with your household",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
