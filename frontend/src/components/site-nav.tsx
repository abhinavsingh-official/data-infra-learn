"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";

const LINKS = [
  { href: "/start", label: "Start" },
  { href: "/learn", label: "Learn" },
  { href: "/learn/reference", label: "Reference" },
  { href: "/learn/edge-cases", label: "Edge Cases" },
  { href: "/learn/interview-questions", label: "Interview Prep" },
  { href: "/daily", label: "Daily" },
  { href: "/profile", label: "Profile" },
];

export function SiteNav() {
  const pathname = usePathname();
  // Longest-href-first match so "/learn/reference" doesn't also light up
  // the plain "/learn" tab.
  const bestMatch = [...LINKS]
    .sort((a, b) => b.href.length - a.href.length)
    .find((link) => pathname === link.href || pathname.startsWith(`${link.href}/`));

  return (
    <nav className="flex items-center gap-1 text-sm">
      {LINKS.map((link) => {
        const active = link.href === bestMatch?.href;
        return (
          <Link
            key={link.href}
            href={link.href}
            className={cn(
              "rounded-md px-3 py-1.5 transition-colors",
              active
                ? "bg-accent font-medium text-accent-foreground"
                : "text-muted-foreground hover:text-foreground",
            )}
          >
            {link.label}
          </Link>
        );
      })}
    </nav>
  );
}
