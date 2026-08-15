import type { Metadata } from "next";
import { IBM_Plex_Sans, Sora } from "next/font/google";
import "./globals.css";
import { AuthProvider } from "@/components/AuthProvider";
import { DatasetBanner } from "@/components/DatasetBanner";
import { Footer } from "@/components/Footer";
import { Header } from "@/components/Header";

// Exactly two families (design-system.md §4): Sora (UI/display) and
// IBM Plex Sans (data/table, tabular figures). Self-hosted by next/font.
const sora = Sora({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  variable: "--font-ui",
  display: "swap",
});

const plex = IBM_Plex_Sans({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  variable: "--font-data",
  display: "swap",
});

export const metadata: Metadata = {
  metadataBase: new URL(process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000"),
  title: {
    default: "Statlas — football analytics that shows its work",
    template: "%s | Statlas",
  },
  description:
    "Per-90 statistics, percentile ranks and the Statlas Index for football players, with a fully published methodology.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${sora.variable} ${plex.variable}`}>
      <body>
        <a className="skip-link no-print" href="#main">
          Skip to content
        </a>
        <DatasetBanner />
        <AuthProvider>
          <Header />
          <main id="main">{children}</main>
          <Footer />
        </AuthProvider>
      </body>
    </html>
  );
}
