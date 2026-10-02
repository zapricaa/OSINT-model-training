import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "ZAPRICA — Autonomous AI OSINT Platform",
  description:
    "Enterprise-grade autonomous AI investigation platform for cybersecurity threat intelligence.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link
          rel="preconnect"
          href="https://fonts.gstatic.com"
          crossOrigin="anonymous"
        />
        <link
          href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap"
          rel="stylesheet"
        />
      </head>
      <body>
        <div className="bg-mesh" />
        {children}
      </body>
    </html>
  );
}
