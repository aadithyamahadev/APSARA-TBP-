import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import Script from "next/script";
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
  title: "APSARA Admin Dashboard",
  description: "Dedicated admin telemetry dashboard for APSARA Security",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const performanceApiShim = `
    (function () {
      if (typeof window === 'undefined' || typeof window.performance === 'undefined') return;
      var p = window.performance;
      if (typeof p.clearMarks !== 'function') p.clearMarks = function () {};
      if (typeof p.clearMeasures !== 'function') p.clearMeasures = function () {};
    })();
  `;

  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col text-slate-900">
        <Script id="performance-api-shim" strategy="beforeInteractive">
          {performanceApiShim}
        </Script>
        {children}
      </body>
    </html>
  );
}
