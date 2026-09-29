"use client";

import { ThemeProvider as NextThemesProvider } from "next-themes";
import type { ComponentProps } from "react";

/** next-themes was already a dependency and already read by ui/sonner.tsx's
 * useTheme() call - but with no provider mounted, that hook always fell back
 * to its "system" default and toasts never actually followed dark mode. This
 * is the missing provider, not a new dependency. */
export function ThemeProvider({ children, ...props }: ComponentProps<typeof NextThemesProvider>) {
  return <NextThemesProvider {...props}>{children}</NextThemesProvider>;
}
