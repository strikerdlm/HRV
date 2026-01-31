// Author: Dr Diego Malpica MD
import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Mission Control - Flight Surgeon",
  description:
    "Comprehensive HRV Analysis Suite for Aerospace Medicine by Dr Diego Malpica MD",
  keywords: [
    "HRV",
    "Heart Rate Variability",
    "Aerospace Medicine",
    "Flight Surgeon",
    "Mission Control",
  ],
  authors: [{ name: "Dr Diego Malpica MD" }],
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={inter.className}>{children}</body>
    </html>
  );
}
