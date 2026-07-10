import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "US Data Center Sustainability Explorer",
  description:
    "Grid carbon intensity and basin-level water stress for 1,474 US data centers — corrected spatial joins, versioned public data.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className="min-h-full flex flex-col">{children}</body>
    </html>
  );
}
