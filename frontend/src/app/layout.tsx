import type { Metadata } from "next";
import { VT323, Press_Start_2P, Geist_Mono } from "next/font/google";
import Link from "next/link";
import "./globals.css";
import { Toaster } from "@/components/ui/sonner";
import { ThemeProvider } from "@/components/theme-provider";
import { ThemeToggle } from "@/components/theme-toggle";
import { SiteFooter } from "@/components/site-footer";
import { SiteNav } from "@/components/site-nav";
import { UserMenu } from "@/components/user-menu";
import { XpBadge } from "@/components/progress/xp-badge";

// An actual retro terminal/arcade font, not just a rounded friendly one -
// VT323 stays legible at body-text length (unlike Press Start 2P, which
// breaks down past a word or two), so it's used everywhere. Press Start
// 2P is reserved for the single short wordmark, where true 8-bit
// chunkiness matters more than paragraph legibility.
const gameSans = VT323({
  variable: "--font-sans",
  weight: "400",
  subsets: ["latin"],
});

const arcadeTitle = Press_Start_2P({
  variable: "--font-arcade",
  weight: "400",
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
      className={`${gameSans.variable} ${arcadeTitle.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col bg-background text-foreground">
        <ThemeProvider attribute="class" defaultTheme="dark" enableSystem>
          <header className="border-b-2 border-panel-edge">
            <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
              <Link href="/" className="font-arcade text-sm leading-none tracking-normal text-foreground">
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
