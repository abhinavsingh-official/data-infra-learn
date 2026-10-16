"use client";

import { useState } from "react";
import { Eye, EyeOff } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { ReferenceSolutionStepDto } from "@/lib/types";

interface ReferenceSolutionProps {
  /** The final, complete query - always shown as the last checkpoint when
   * `steps` is given, or as the only content when it isn't. */
  solution: string;
  note?: string;
  /** Staged breakdown of the same query, one edge case handled at a time -
   * this is what actually teaches "one basic query becomes the full fix",
   * instead of just handing over the finished answer. */
  steps?: ReferenceSolutionStepDto[];
}

/** Hidden-until-revealed by design (explicit user choice over "shown
 * immediately") - it's a worked example to check your own attempt
 * against, not something to copy before trying. */
export function ReferenceSolution({ solution, note, steps }: ReferenceSolutionProps) {
  const [revealed, setRevealed] = useState(false);

  if (!revealed) {
    return (
      <Button variant="outline" size="sm" onClick={() => setRevealed(true)} className="gap-2">
        <Eye className="size-4" />
        {steps && steps.length > 0 ? "See how the query builds up" : "See a worked example"}
      </Button>
    );
  }

  return (
    <div className="space-y-3 rounded-lg border bg-muted/50 p-3">
      <div className="flex items-center justify-between">
        <p className="text-xs font-medium text-muted-foreground">
          {steps && steps.length > 0 ? "Query evolution - worked example" : "Worked example"}
        </p>
        <Button variant="ghost" size="sm" onClick={() => setRevealed(false)} className="h-auto gap-1.5 px-2 py-1 text-xs">
          <EyeOff className="size-3.5" />
          Hide
        </Button>
      </div>

      {steps && steps.length > 0 ? (
        <ol className="space-y-3">
          {steps.map((step) => (
            <li key={step.title} className="space-y-1.5 border-l-2 border-border pl-3">
              <p className="text-sm font-medium">{step.title}</p>
              <pre className="whitespace-pre-wrap break-words rounded-md bg-background p-3 font-mono text-xs">{step.sql}</pre>
              {step.note && <p className="text-xs text-muted-foreground">{step.note}</p>}
            </li>
          ))}
        </ol>
      ) : (
        <>
          <pre className="whitespace-pre-wrap break-words rounded-md bg-background p-3 font-mono text-xs">{solution}</pre>
          {note && <p className="text-xs text-muted-foreground">{note}</p>}
        </>
      )}
    </div>
  );
}
