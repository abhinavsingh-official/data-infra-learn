import type { Metadata } from "next";
import { Baloo_2, Geist_Mono } from "next/font/google";
import Link from "next/link";
import "./globals.css";
import { Toaster } from "@/components/ui/sonner";
import { ThemeProvider } from "@/components/theme-provider";
import { ThemeToggle } from "@/components/theme-toggle";
import { SiteFooter } from "@/components/site-footer";
import { SiteNav } from "@/components/site-nav";
import { UserMenu } from "@/components/user-menu";
import { XpBadge } from "@/components/progress/xp-badge";

// Chunky, rounded, game-UI-friendly - and unlike the previous Geist Sans
// setup, this one's CSS variable is actually named --font-sans to match
// what globals.css's @theme inline block reads (the old mismatched
// --font-geist-sans name meant the custom font was never really applying
// at all - every page was silently falling back to the browser default).
const gameSans = Baloo_2({
  variable: "--font-sans",
  weight: ["400", "500", "600", "700", "800"],
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Learndata",
  description: "Learn how ETL actually breaks, one storage approach at a time.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="en"
      suppressHydrationWarning
      className={`${gameSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col bg-background text-foreground">
        <ThemeProvider attribute="class" defaultTheme="dark" enableSystem>
          <header className="border-b">
            <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
              <Link href="/" className="font-semibold tracking-tight">
                Learndata
              </Link>
              <div className="flex items-center gap-4">
                <SiteNav />
                <XpBadge />
                <ThemeToggle />
                <UserMenu />
              </div>
            </div>
          </header>
          <main className="mx-auto w-full max-w-7xl flex-1 px-6 py-8">{children}</main>
          <SiteFooter />
          <Toaster />
        </ThemeProvider>
      </body>
    </html>
  );
}
