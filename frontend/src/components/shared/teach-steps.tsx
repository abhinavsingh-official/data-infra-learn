"use client";

import { useState } from "react";
import { ArrowLeft, ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import type { TeachStepDto } from "@/lib/types";

/** A Duolingo-style stepped lesson player - one short idea per screen,
 * advanced with Next/Back instead of one dense paragraph. Resets back to
 * step 0 whenever the step sequence itself changes (a different node was
 * opened), via the `key` prop the caller passes on this component. */
export function TeachSteps({ steps }: { steps: TeachStepDto[] }) {
  const [index, setIndex] = useState(0);
  const step = steps[index];
  const isLast = index === steps.length - 1;

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-1.5">
        {steps.map((_, i) => (
          <span
            key={i}
            className={cn(
              "h-1.5 flex-1 rounded-full transition-colors",
              i <= index ? "bg-primary" : "bg-muted",
            )}
          />
        ))}
      </div>

      <div className="flex min-h-80 flex-col justify-center space-y-6 rounded-xl border bg-card p-8">
        <p className="text-lg leading-relaxed text-balance">{step.body}</p>
        {step.sql && (
          <pre className="overflow-x-auto rounded-md border bg-muted/40 p-4 font-mono text-sm">{step.sql}</pre>
        )}
      </div>

      <div className="flex items-center justify-between">
        <Button variant="ghost" size="sm" disabled={index === 0} onClick={() => setIndex((i) => i - 1)}>
          <ArrowLeft className="size-4" />
          Back
        </Button>
        <span className="text-xs text-muted-foreground">
          {index + 1} / {steps.length}
        </span>
        <Button
          size="sm"
          disabled={isLast}
          onClick={() => setIndex((i) => Math.min(i + 1, steps.length - 1))}
        >
          Next
          <ArrowRight className="size-4" />
        </Button>
      </div>
    </div>
  );
}
