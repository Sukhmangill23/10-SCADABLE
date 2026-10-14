import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { AppProviders } from "@/components/providers/AppProviders";
import { isClerkConfigured } from "@/lib/auth/config";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Live SWOT",
  description: "Internal competitor intelligence for SCADABLE",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const clerkEnabled = isClerkConfigured();

  return (
    <html lang="en">
      <body
        className={`${geistSans.className} ${geistSans.variable} ${geistMono.variable}`}
      >
        <AppProviders clerkEnabled={clerkEnabled}>{children}</AppProviders>
      </body>
    </html>
  );
}
