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

// VT323 (retro terminal font) stays legible at body-text length, unlike
// Press Start 2P, which breaks down past a word or two - that one's
// reserved for the short wordmark instead.
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
              <div className="flex items-center gap-3">
                <Link href="/" className="font-arcade text-sm leading-none tracking-normal text-foreground">
                  Learndata
                </Link>
                <span className="hidden text-sm text-muted-foreground sm:inline">
                  by Abhinav Singh
                </span>
                <a
                  href="https://github.com/abhinavsingh-official"
                  target="_blank"
                  rel="noopener noreferrer"
                  aria-label="Abhinav Singh on GitHub"
                  className="text-muted-foreground transition-colors hover:text-foreground"
                >
                  <svg viewBox="0 0 24 24" className="size-4" fill="currentColor" aria-hidden="true">
                    <path d="M12 .5C5.73.5.5 5.74.5 12.02c0 5.02 3.26 9.28 7.78 10.78.57.1.78-.25.78-.55 0-.27-.01-1.17-.02-2.12-3.17.69-3.84-1.35-3.84-1.35-.52-1.32-1.27-1.67-1.27-1.67-1.04-.71.08-.7.08-.7 1.15.08 1.76 1.18 1.76 1.18 1.02 1.75 2.68 1.25 3.33.95.1-.74.4-1.25.72-1.54-2.53-.29-5.19-1.27-5.19-5.63 0-1.24.44-2.26 1.17-3.05-.12-.29-.51-1.45.11-3.02 0 0 .96-.31 3.14 1.16a10.9 10.9 0 0 1 5.72 0c2.18-1.47 3.14-1.16 3.14-1.16.62 1.57.23 2.73.11 3.02.73.79 1.17 1.81 1.17 3.05 0 4.37-2.67 5.33-5.21 5.62.41.36.77 1.08.77 2.17 0 1.57-.01 2.83-.01 3.22 0 .3.2.66.79.55C20.24 21.29 23.5 17.04 23.5 12.02 23.5 5.74 18.27.5 12 .5Z" />
                  </svg>
                </a>
              </div>
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
