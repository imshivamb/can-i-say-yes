import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Can I Say Yes? · Autopilot",
  description: "Evidence-backed commitment feasibility for Northstar Creative.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
