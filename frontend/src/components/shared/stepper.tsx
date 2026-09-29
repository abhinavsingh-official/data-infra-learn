import { Check } from "lucide-react";
import { cn } from "@/lib/utils";
import type { PhaseSlug } from "@/lib/phase-theme";
import { PHASE_THEME } from "@/lib/phase-theme";

interface StepperProps {
  steps: string[];
  currentIndex: number;
  phase: PhaseSlug;
}

/** The "where am I in this lesson" progress bar every phase page uses -
 * numbered circles connected by a line, filled in as you go, colored by
 * that phase's own accent. Purely presentational; each phase's own
 * session-panel owns which step is actually active. */
export function Stepper({ steps, currentIndex, phase }: StepperProps) {
  const theme = PHASE_THEME[phase];
  return (
    <ol className="flex w-full items-start">
      {steps.map((step, index) => {
        const done = index < currentIndex;
        const active = index === currentIndex;
        return (
          <li key={step} className="flex flex-1 flex-col items-center last:flex-none">
            <div className="flex w-full items-center">
              <div
                className={cn(
                  "flex size-8 shrink-0 items-center justify-center rounded-full border-2 text-sm font-medium transition-colors",
                  done && `${theme.bgSolid} border-transparent text-white`,
                  active && `border-current ${theme.text}`,
                  !done && !active && "border-border text-muted-foreground",
                )}
              >
                {done ? <Check className="size-4" /> : index + 1}
              </div>
              {index < steps.length - 1 && (
                <div className={cn("mx-2 h-0.5 flex-1", done ? theme.bgSolid : "bg-border")} />
              )}
            </div>
            <span
              className={cn(
                "mt-2 max-w-24 text-center text-xs",
                active ? `font-medium ${theme.text}` : "text-muted-foreground",
              )}
            >
              {step}
            </span>
          </li>
        );
      })}
    </ol>
  );
}
