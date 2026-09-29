"use client";

import { useState } from "react";
import { Eye, EyeOff } from "lucide-react";
import { Button } from "@/components/ui/button";

interface ReferenceSolutionProps {
  /** The optimized/reference query or command, shown verbatim once revealed. */
  solution: string;
  /** Short note on why this shape is the better one (index used, why a CTE
   * over a subquery, etc.) - the teaching payoff, not just the answer. */
  note?: string;
}

/** Hidden-until-revealed by design (explicit user choice over "shown
 * immediately") - it's a worked example to check your own attempt
 * against, not something to copy before trying. */
export function ReferenceSolution({ solution, note }: ReferenceSolutionProps) {
  const [revealed, setRevealed] = useState(false);

  if (!revealed) {
    return (
      <Button variant="outline" size="sm" onClick={() => setRevealed(true)} className="gap-2">
        <Eye className="size-4" />
        See a worked example
      </Button>
    );
  }

  return (
    <div className="space-y-2 rounded-lg border bg-muted/50 p-3">
      <div className="flex items-center justify-between">
        <p className="text-xs font-medium text-muted-foreground">Worked example</p>
        <Button variant="ghost" size="sm" onClick={() => setRevealed(false)} className="h-auto gap-1.5 px-2 py-1 text-xs">
          <EyeOff className="size-3.5" />
          Hide
        </Button>
      </div>
      <pre className="overflow-x-auto rounded-md bg-background p-3 font-mono text-xs">{solution}</pre>
      {note && <p className="text-xs text-muted-foreground">{note}</p>}
    </div>
  );
}
